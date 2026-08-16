"""构想台 DISCUSS / Stop；确认取当前 Thread。"""
from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from ..acp.skill_loader import resolve_skill_root
from ..workflow_agent.pi_rpc import PiRpcRunner, _assistant_text, parse_rpc_event
from .asset_bridge import ComfyTVAssetBridge
from .context_compiler import compile_stage_context, creative_system_prompt
from .identity import validate_stage_id, validate_thread_id
from .project_repository import CreativeProjectRepository
from .stage_registry import load_pipeline
from .stage_service import CreativeStageService


class CreativeChatError(RuntimeError):
    """聊天失败。"""


@dataclass(slots=True)
class _Active:
    request_id: str
    runner: Any
    generated: str = ""


class CreativeChatService:
    def __init__(
        self,
        repository: CreativeProjectRepository | None = None,
        rpc_runner: Any | None = None,
        *,
        skill_directory_resolver: Callable[[str], Path] | None = None,
        event_publisher: Callable[[dict[str, Any]], None] | None = None,
        asset_bridge: ComfyTVAssetBridge | None = None,
        stage_service: CreativeStageService | None = None,
    ) -> None:
        self.repository = repository or CreativeProjectRepository()
        self.rpc_runner = rpc_runner or PiRpcRunner()
        self.skill_directory_resolver = skill_directory_resolver or self._default_skill_dir
        self.event_publisher = event_publisher
        self.asset_bridge = asset_bridge or ComfyTVAssetBridge()
        self.stage_service = stage_service or CreativeStageService(self.repository)
        self._active: dict[tuple[str, str], _Active] = {}
        self._lock = threading.RLock()

    @staticmethod
    def _default_skill_dir(skill_id: str) -> Path:
        root = resolve_skill_root("")
        return Path(root) / skill_id

    def _publish(self, event: dict[str, Any], events: list[dict[str, Any]]) -> None:
        events.append(event)
        if self.event_publisher:
            self.event_publisher(event)

    def _runner(self) -> Any:
        if isinstance(self.rpc_runner, PiRpcRunner):
            return PiRpcRunner(self.rpc_runner.profile, probe=self.rpc_runner.probe)
        return self.rpc_runner

    def discuss(
        self,
        *,
        project_id: str,
        stage_id: str,
        message: str,
        thread_id: str = "",
        skill_id: str = "",
        skill_scope: str = "stage",
        asset_ref_ids: list[str] | None = None,
    ) -> dict[str, Any]:
        stage = validate_stage_id(stage_id)
        if not str(message or "").strip():
            raise CreativeChatError("message is required")
        if skill_scope not in {"stage", "turn"}:
            raise CreativeChatError("skill_scope must be stage|turn")
        pipeline = load_pipeline()
        spec = pipeline.stage(stage)
        resolved_skill = (skill_id or spec.skill_id).strip()
        tid = thread_id or self.repository.ensure_main_thread(project_id, stage)
        tid = validate_thread_id(tid)
        self.repository.set_current_thread(project_id, stage, tid)

        request_id = f"req_{uuid.uuid4().hex}"
        message_id = f"msg_{uuid.uuid4().hex}"
        events: list[dict[str, Any]] = []

        refs = self.repository.read_asset_refs(project_id)
        if asset_ref_ids:
            wanted = set(asset_ref_ids)
            refs = [r for r in refs if r.get("asset_ref_id") in wanted]
        compiled = self.asset_bridge.compile_refs(
            refs,
            cache_dir=self.repository.paths(project_id).cache,
        )
        context_text = compile_stage_context(
            self.repository,
            project_id,
            stage,
            asset_context_blocks=[compiled.text] if compiled.text else None,
        )
        user_payload = f"{context_text}\n\n[USER_MESSAGE]\n{message.strip()}"

        self.repository.append_thread_record(
            project_id,
            stage,
            tid,
            {
                "role": "user",
                "content": message.strip(),
                "message_id": message_id,
                "request_id": request_id,
                "skill_id": resolved_skill,
                "skill_scope": skill_scope,
            },
        )
        self.stage_service.mark_draft(project_id, stage)

        key = (project_id, tid)
        runner = self._runner()
        with self._lock:
            self._active[key] = _Active(request_id=request_id, runner=runner)

        generated = ""
        status = "complete"
        error = ""
        try:
            skill_dir = self.skill_directory_resolver(resolved_skill)
            stream = runner.run(
                prompt=user_payload,
                skill_directory=skill_dir,
                session_dir=self.repository.paths(project_id).root,
                mode="DISCUSS",
            )
            for raw_event in stream:
                event = parse_rpc_event(raw_event) if not isinstance(raw_event, dict) else raw_event
                if not isinstance(event, dict):
                    continue
                etype = str(event.get("type") or event.get("event") or "")
                if etype in {"delta", "text_delta", "assistant_delta"}:
                    chunk = str(event.get("text") or event.get("delta") or event.get("content") or "")
                    generated += chunk
                    with self._lock:
                        if key in self._active:
                            self._active[key].generated = generated
                    self._publish(
                        {
                            "type": "delta",
                            "project_id": project_id,
                            "stage_id": stage,
                            "thread_id": tid,
                            "request_id": request_id,
                            "text": chunk,
                        },
                        events,
                    )
                elif etype in {"error", "failed"}:
                    status = "error"
                    error = str(event.get("error") or event.get("message") or "pi error")
                elif etype in {"interrupted", "stopped"}:
                    status = "stopped"
            if hasattr(runner, "final_text"):
                final = getattr(runner, "final_text")
                if callable(final):
                    maybe = final()
                    if maybe:
                        generated = str(maybe)
                elif final:
                    generated = str(final)
            if not generated and hasattr(runner, "events"):
                generated = _assistant_text(getattr(runner, "events") or [])
        except Exception as exc:  # noqa: BLE001
            status = "error"
            error = str(exc) or "discuss failed"
        finally:
            with self._lock:
                self._active.pop(key, None)

        self.repository.append_thread_record(
            project_id,
            stage,
            tid,
            {
                "role": "assistant",
                "content": generated,
                "message_id": f"msg_{uuid.uuid4().hex}",
                "request_id": request_id,
                "status": status,
                "error": error,
                "skill_id": resolved_skill,
                "skill_scope": skill_scope,
            },
        )
        ready = self.stage_service.evaluate_ready(project_id, stage, tid)
        self._publish(
            {
                "type": "end",
                "project_id": project_id,
                "stage_id": stage,
                "thread_id": tid,
                "request_id": request_id,
                "status": status,
                "text": generated,
                "error": error,
                "ready": ready.get("ready"),
            },
            events,
        )
        if status == "error":
            raise CreativeChatError(error or "discuss failed")
        return {
            "status": status,
            "request_id": request_id,
            "message_id": message_id,
            "project_id": project_id,
            "stage_id": stage,
            "thread_id": tid,
            "text": generated,
            "events": events,
            "ready": ready,
        }

    def stop(self, *, project_id: str, thread_id: str) -> dict[str, Any]:
        tid = validate_thread_id(thread_id)
        key = (project_id, tid)
        with self._lock:
            active = self._active.get(key)
            if not active:
                return {"status": "idle", "project_id": project_id, "thread_id": tid}
            runner = active.runner
            request_id = active.request_id
        stop = getattr(runner, "stop", None)
        if callable(stop):
            stop()
        interrupt = getattr(runner, "interrupt", None)
        if callable(interrupt):
            interrupt()
        return {
            "status": "stopping",
            "project_id": project_id,
            "thread_id": tid,
            "request_id": request_id,
        }

    def commit_text_via_runner(
        self,
        *,
        project_id: str,
        stage_id: str,
        thread_id: str,
        skill_id: str,
        user_message: str,
        draft_text: str = "",
    ) -> str:
        skill_dir = self.skill_directory_resolver(skill_id)
        context_text = compile_stage_context(self.repository, project_id, stage_id)
        _ = creative_system_prompt(stage_id, skill_id)
        prompt = (
            f"{context_text}\n\n[DRAFT]\n{draft_text}\n\n[USER_MESSAGE]\n{user_message}\n\n"
            "请仅输出正式确认结果，包含唯一 ryan-stage-export 块。"
        )
        runner = self._runner()
        generated = ""
        stream = runner.run(
            prompt=prompt,
            skill_directory=skill_dir,
            session_dir=self.repository.paths(project_id).root,
            mode="COMMIT",
        )
        for raw_event in stream:
            event = parse_rpc_event(raw_event) if not isinstance(raw_event, dict) else raw_event
            if not isinstance(event, dict):
                continue
            etype = str(event.get("type") or event.get("event") or "")
            if etype in {"delta", "text_delta", "assistant_delta"}:
                generated += str(event.get("text") or event.get("delta") or event.get("content") or "")
        if hasattr(runner, "final_text"):
            final = getattr(runner, "final_text")
            if callable(final):
                maybe = final()
                if maybe:
                    generated = str(maybe)
            elif final:
                generated = str(final)
        return generated


__all__ = ["CreativeChatError", "CreativeChatService"]
