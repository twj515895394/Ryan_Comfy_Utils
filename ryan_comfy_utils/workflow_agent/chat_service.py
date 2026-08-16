"""Workflow Agent DISCUSS、私有 Draft、Stop 和 Retry 幂等。"""
from __future__ import annotations

import json
import uuid
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping

from .assets import WorkflowAgentAssetStore
from .context_select import ContextViewPolicy, render_context_view
from .models import RyanContext
from .repository import WorkflowAgentRepository
from .skill_contract import SkillContractError, load_skill_contract
from .state import AgentState
from .pi_rpc import PiRpcRunner, _assistant_text, parse_rpc_event


class ChatServiceError(RuntimeError):
    """Chat 请求失败。"""


def _as_json(value: Any) -> Any:
    if hasattr(value, "to_dict"):
        return value.to_dict()
    if isinstance(value, Mapping):
        return {str(k): _as_json(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_as_json(v) for v in value]
    return value


def _context(value: Any, workflow_id: str) -> RyanContext:
    if value is None:
        return RyanContext(workflow_id=workflow_id)
    if isinstance(value, RyanContext):
        if value.workflow_id != workflow_id:
            raise ChatServiceError("upstream context workflow mismatch")
        return value
    if isinstance(value, Mapping):
        payload = dict(value)
        payload.setdefault("workflow_id", workflow_id)
        result = RyanContext.from_dict(payload)
        if result.workflow_id != workflow_id:
            raise ChatServiceError("upstream context workflow mismatch")
        return result
    raise ChatServiceError("upstream_context must be an object")


def _upstream_ids(context: RyanContext) -> list[str]:
    return sorted({entry.entry_id for entry in context.entries if entry.status == "active"})


@dataclass(slots=True)
class _ActiveRequest:
    request_id: str
    message_id: str
    runner: Any
    generated: str = ""


class WorkflowAgentChatService:
    """单 Agent 私有会话服务；绝不把 Chat 记录写进 RYAN_CONTEXT。"""

    def __init__(
        self,
        repository: WorkflowAgentRepository | None = None,
        rpc_runner: Any | None = None,
        *,
        skill_directory_resolver: Callable[[str], Path] | None = None,
        event_publisher: Callable[[dict[str, Any]], None] | None = None,
    ) -> None:
        self.repository = repository or WorkflowAgentRepository()
        self.asset_store = WorkflowAgentAssetStore(self.repository)
        self.rpc_runner = rpc_runner or PiRpcRunner()
        self.skill_directory_resolver = skill_directory_resolver
        self.event_publisher = event_publisher
        self._active: dict[tuple[str, str], _ActiveRequest] = {}
        self._lock = threading.RLock()

    def _runner_for_request(self) -> Any:
        # 默认 Pi Runner 每个 Agent 请求独立进程，避免多面板并发互相覆盖 stop 句柄。
        if isinstance(self.rpc_runner, PiRpcRunner):
            return PiRpcRunner(self.rpc_runner.profile, probe=self.rpc_runner.probe)
        return self.rpc_runner

    def _publish(self, event: dict[str, Any], events: list[dict[str, Any]]) -> None:
        events.append(event)
        if self.event_publisher:
            self.event_publisher(event)

    @staticmethod
    def _find_retry(records: list[dict[str, Any]], request_id: str, message_id: str) -> tuple[dict[str, Any] | None, str]:
        response = None
        draft = ""
        for record in records:
            if record.get("role") == "assistant" and (
                (request_id and record.get("request_id") == request_id)
                or (message_id and record.get("message_id") == message_id)
            ):
                response = record
            if record.get("role") == "assistant":
                draft += str(record.get("content", "")) if record.get("request_id") == request_id else ""
        return response, draft

    def _prompt(
        self,
        message: str,
        upstream: RyanContext,
        assets: Any,
        draft: Any,
        contract: Mapping[str, Any],
    ) -> str:
        policy = ContextViewPolicy()
        context_view = render_context_view(
            upstream,
            contract.get("accepts_context_kinds", ("*",)),
            mode="summary",
            policy=policy,
        )
        assets_text = json.dumps(_as_json(assets or []), ensure_ascii=False)
        return "\n".join(
            (
                "RYAN_AGENT_MODE=DISCUSS",
                "[UPSTREAM_CONTEXT]",
                context_view,
                "[/UPSTREAM_CONTEXT]",
                "[ASSETS]",
                assets_text[: policy.asset_limit],
                "[/ASSETS]",
                "[CURRENT_DRAFT]",
                str(draft or "")[: policy.draft_limit],
                "[/CURRENT_DRAFT]",
                "[USER_MESSAGE]",
                message[: policy.message_limit],
                "[/USER_MESSAGE]",
            )
        )

    def discuss(self, payload: Mapping[str, Any] | None = None, **kwargs: Any) -> dict[str, Any]:
        body = dict(payload or {})
        body.update(kwargs)
        workflow_id = str(body.get("workflow_id", ""))
        agent_uid = str(body.get("agent_uid", ""))
        skill_id = str(body.get("skill_id", ""))
        message = str(body.get("message", body.get("user_message", "")))
        request_id = str(body.get("request_id", ""))
        message_id = str(body.get("message_id", ""))
        if not workflow_id or not agent_uid or not skill_id or not message:
            raise ChatServiceError("workflow_id, agent_uid, skill_id and message are required")
        if not request_id:
            request_id = message_id or f"request-{uuid.uuid4().hex}"
        if not message_id:
            message_id = request_id
        try:
            directory, contract = load_skill_contract(skill_id, body, self.skill_directory_resolver)
        except SkillContractError as exc:
            raise ChatServiceError(str(exc)) from exc
        paths = self.repository.initialize_scope(workflow_id, agent_uid)
        state = self.repository.read_state(workflow_id, agent_uid)
        state.skill_id = skill_id
        if body.get("agent_name"):
            state.agent_name = str(body["agent_name"])[:128]
        upstream = _context(body.get("upstream_context", body.get("context")), workflow_id)
        raw_assets = body.get("asset_refs", body.get("assets"))
        if raw_assets is None:
            raw_assets = upstream.assets
        assets = self.asset_store.prepare_context(workflow_id, agent_uid, raw_assets)
        records = self.repository.read_pi_session(workflow_id, agent_uid)
        prior, _ = self._find_retry(records, request_id, message_id)
        latest = self.repository.read_latest_commit(workflow_id, agent_uid)
        old_ids = sorted(str(item) for item in latest.get("upstream_entry_ids", [])) if latest else []
        changed = bool(latest) and old_ids != _upstream_ids(upstream)
        base = {"workflow_id": workflow_id, "agent_uid": agent_uid, "request_id": request_id, "message_id": message_id}
        if prior is not None:
            response_text = str(prior.get("content", ""))
            return {**base, "status": "completed", "draft": state.draft, "response_text": response_text,
                    "events": [{**base, "status": "completed", "type": "completed", "text": response_text}],
                    "upstream_changed": changed}
        if not any(
            record.get("role") == "user" and (
                (request_id and record.get("request_id") == request_id)
                or (message_id and record.get("message_id") == message_id)
            ) for record in records
        ):
            self.repository.append_pi_session(workflow_id, agent_uid, {
                "role": "user", "request_id": request_id, "message_id": message_id, "content": message,
            })
        state.status = "generating"
        self.repository.write_state(workflow_id, agent_uid, state)
        events: list[dict[str, Any]] = []
        self._publish({**base, "type": "status", "status": "generating"}, events)
        runner = self._runner_for_request()
        active = _ActiveRequest(request_id, message_id, runner)
        with self._lock:
            self._active[(workflow_id, agent_uid)] = active
        response_parts: list[str] = []
        final_response = ""
        try:
            result = runner.run(
                skill_directory=directory, session_dir=paths.root,
                prompt=self._prompt(message, upstream, assets, state.draft, contract), mode="DISCUSS",
                on_event=None,
            )
            for raw_event in result:
                event = parse_rpc_event(raw_event) or {"status": "delta", "type": "delta"}
                event_type = str(event.get("type", ""))
                text = str(event.get("text", ""))
                if event_type == "agent_end":
                    final_response = str(
                        event.get("final_text")
                        or _assistant_text(event.get("messages"))
                        or text
                    )
                    if final_response:
                        active.generated = final_response
                elif text:
                    response_parts.append(text)
                    active.generated = "".join(response_parts)
                self._publish({**event, **base}, events)
            response_text = final_response if final_response.strip() else "".join(response_parts)
            if not response_text.strip():
                raise ChatServiceError("Pi RPC returned an empty response")
            state.draft = response_text
            state.status = "idle"
            self.repository.append_pi_session(workflow_id, agent_uid, {
                "role": "assistant", "request_id": request_id, "message_id": message_id, "content": response_text,
            })
            self.repository.write_state(workflow_id, agent_uid, state)
            self._publish({**base, "type": "completed", "status": "completed", "text": response_text}, events)
            return {**base, "status": "completed", "draft": response_text, "response_text": response_text,
                    "events": events, "upstream_changed": changed}
        except Exception as exc:
            partial = active.generated
            stopped = getattr(runner, "status", "") == "stopped"
            state.draft = partial or state.draft
            state.status = "stopped" if stopped else "error"
            self.repository.write_state(workflow_id, agent_uid, state)
            status = "stopped" if stopped else "error"
            error_message = "Pi RPC stopped" if stopped else str(exc) or "Pi RPC failed"
            self._publish({**base, "type": status, "status": status, "text": partial,
                           "error": error_message}, events)
            if stopped:
                return {**base, "status": status, "draft": state.draft, "response_text": partial,
                        "events": events, "upstream_changed": changed}
            raise ChatServiceError(error_message) from exc
        finally:
            with self._lock:
                self._active.pop((workflow_id, agent_uid), None)

    def stop(self, workflow_id: str, agent_uid: str, *, request_id: str = "", message_id: str = "") -> dict[str, Any]:
        with self._lock:
            active = self._active.get((workflow_id, agent_uid))
        if active is None:
            state = self.repository.read_state(workflow_id, agent_uid)
            return {"status": "stopped", "workflow_id": workflow_id, "agent_uid": agent_uid,
                    "draft": state.draft, "request_id": request_id, "message_id": message_id}
        stop = getattr(active.runner, "stop", None)
        if callable(stop):
            stop()
        state = self.repository.read_state(workflow_id, agent_uid)
        state.draft = active.generated or state.draft
        state.status = "stopped"
        self.repository.write_state(workflow_id, agent_uid, state)
        return {"status": "stopped", "workflow_id": workflow_id, "agent_uid": agent_uid,
                "request_id": request_id or active.request_id, "message_id": message_id or active.message_id,
                "draft": state.draft, "commit_revision": state.commit_revision}

    def reset(self, workflow_id: str, agent_uid: str) -> dict[str, Any]:
        paths = self.repository.scope_paths(workflow_id, agent_uid, create=True)
        paths.pi_session.write_text("", encoding="utf-8")
        state = self.repository.read_state(workflow_id, agent_uid)
        state.draft = ""
        state.status = "idle"
        self.repository.write_state(workflow_id, agent_uid, state)
        return {"status": "idle", "workflow_id": workflow_id, "agent_uid": agent_uid,
                "draft": "", "commit_revision": state.commit_revision,
                "latest_entry_id": state.latest_entry_id}

    def get_agent(self, workflow_id: str, agent_uid: str) -> dict[str, Any]:
        state = self.repository.read_state(workflow_id, agent_uid)
        records = self.repository.read_pi_session(workflow_id, agent_uid)
        latest = self.repository.read_latest_commit(workflow_id, agent_uid)
        return {"status": state.status, "workflow_id": workflow_id, "agent_uid": agent_uid,
                "skill_id": state.skill_id, "agent_name": state.agent_name, "draft": state.draft,
                "message_count": len(records), "messages": records, "commit_revision": state.commit_revision,
                "latest_entry_id": state.latest_entry_id or latest.get("entry_id")}


ChatService = WorkflowAgentChatService
__all__ = ["ChatServiceError", "ChatService", "WorkflowAgentChatService"]
