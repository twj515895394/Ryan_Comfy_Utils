"""Workflow Agent HTTP API；无 ComfyUI 时可安全导入。"""
from __future__ import annotations

import asyncio
import json
import os
import re
import tempfile
from pathlib import Path
from typing import Any, Mapping

from .assets import MAX_ASSET_BYTES, WorkflowAgentAssetStore
from .chat_service import ChatServiceError, WorkflowAgentChatService
from .commit_service import CommitServiceError, WorkflowAgentCommitService
from .models import RyanContext
from .repository import WorkflowAgentRepository

try:  # ComfyUI is optional for unit tests and library imports.
    from aiohttp import web  # type: ignore
except Exception:  # pragma: no cover - exercised only outside ComfyUI
    web = None  # type: ignore


_REDACTIONS = (
    (re.compile(r"(?i)(api[_-]?key|token|secret)=\S+"), r"\1=[redacted]"),
    (re.compile(r"(?i)bearer\s+[a-z0-9._-]+"), "Bearer [redacted]"),
)


def _safe_error(exc: Exception) -> str:
    message = str(exc) or "request failed"
    for pattern, replacement in _REDACTIONS:
        message = pattern.sub(replacement, message)
    # Do not return machine-specific paths or exception tracebacks.
    if "no such file" in message.lower() or "not found" in message.lower():
        return "requested resource was not found"
    if "traceback" in message.lower() or "\\" in message or "/" in message and ":" in message:
        return "request failed"
    return message[:240]


def _response(payload: Mapping[str, Any], status: int = 200) -> Any:
    if web is not None:
        return web.json_response(dict(payload), status=status)
    return dict(payload)


def error_response(exc: Exception, status: int = 400) -> Any:
    return _response({"status": "error", "error": _safe_error(exc)}, status)


def _status_for(exc: Exception) -> int:
    if isinstance(exc, (ChatServiceError, CommitServiceError, ValueError, TypeError)):
        return 400
    return 500


async def _json_body(request: Any) -> dict[str, Any]:
    payload = await request.json()
    if not isinstance(payload, dict):
        raise ValueError("JSON body must be an object")
    return payload

async def _asset_body(request: Any) -> tuple[dict[str, Any], str | None]:
    """读取 JSON 或 ComfyUI multipart，并把上传文件暂存为普通文件。"""
    content_type = str(getattr(request, "content_type", "") or "")
    if not content_type.startswith("multipart/") or not hasattr(request, "multipart"):
        return await _json_body(request), None
    body: dict[str, Any] = {}
    temporary_path: str | None = None
    reader = await request.multipart()
    async for part in reader:
        field_name = str(getattr(part, "name", "") or "")
        filename = getattr(part, "filename", None)
        if filename:
            safe_filename = Path(str(filename)).name or "upload"
            suffix = Path(safe_filename).suffix[:20]
            descriptor, temporary_path = tempfile.mkstemp(prefix="ryan-asset-", suffix=suffix)
            body["display_name"] = safe_filename
            headers = getattr(part, "headers", {}) or {}
            body["mime_type"] = headers.get("Content-Type") or None
            total = 0
            try:
                with os.fdopen(descriptor, "wb") as handle:
                    while True:
                        chunk = await part.read_chunk(1024 * 1024)
                        if not chunk:
                            break
                        total += len(chunk)
                        if total > MAX_ASSET_BYTES:
                            raise ValueError(f"asset exceeds maximum size of {MAX_ASSET_BYTES} bytes")
                        handle.write(chunk)
            except Exception:
                Path(temporary_path).unlink(missing_ok=True)
                raise
            body["source_path"] = temporary_path
        else:
            body[field_name] = await part.text()
    return body, temporary_path


def list_skills(skill_root: str | Path | None = None) -> list[dict[str, Any]]:
    if skill_root is None:
        from ..acp.skill_loader import resolve_skill_root
        root = resolve_skill_root("")
    else:
        root = Path(skill_root)
    result: list[dict[str, Any]] = []
    if not root.exists():
        return result
    for directory in sorted(path for path in root.iterdir() if path.is_dir()):
        contract_path = directory / "agent-contract.json"
        if not contract_path.is_file():
            continue
        try:
            contract = json.loads(contract_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(contract, dict):
            result.append({"skill_id": directory.name, **contract})
    return result


def register_routes(
    prompt_server: Any | None = None,
    *,
    chat_service: WorkflowAgentChatService | None = None,
    commit_service: WorkflowAgentCommitService | None = None,
    repository: WorkflowAgentRepository | None = None,
    asset_store: WorkflowAgentAssetStore | None = None,
) -> Any:
    """在 PromptServer 上注册路由并返回注册后的 service 对象。"""
    if prompt_server is None:
        try:
            from server import PromptServer  # type: ignore
            prompt_server = getattr(PromptServer, "instance", None)
        except Exception:
            prompt_server = None
    repository = repository or (chat_service.repository if chat_service else None) or (commit_service.repository if commit_service else None) or WorkflowAgentRepository()
    event_publisher = None
    send_sync = getattr(prompt_server, "send_sync", None)
    if callable(send_sync):
        def publish_agent_event(event: dict[str, Any]) -> None:
            try:
                send_sync("ryan_agent_event", event, getattr(prompt_server, "client_id", None))
            except TypeError:
                send_sync("ryan_agent_event", event)

        event_publisher = publish_agent_event
    if chat_service is None:
        chat_service = WorkflowAgentChatService(repository, event_publisher=event_publisher)
    commit_service = commit_service or WorkflowAgentCommitService(repository, getattr(chat_service, "rpc_runner", None))
    asset_store = asset_store or WorkflowAgentAssetStore(repository)
    if prompt_server is None or not hasattr(prompt_server, "routes"):
        return {"chat_service": chat_service, "commit_service": commit_service, "asset_store": asset_store}
    routes = prompt_server.routes

    @routes.get("/ryan/agent/skills")
    async def skills(request: Any) -> Any:
        try:
            return _response({"status": "ok", "skills": list_skills(request.query.get("skill_root"))})
        except Exception as exc:
            return error_response(exc, _status_for(exc))

    @routes.get("/ryan/agent/workflows/{workflow_id}/agents/{agent_uid}")
    async def agent(request: Any) -> Any:
        try:
            workflow_id, agent_uid = request.match_info["workflow_id"], request.match_info["agent_uid"]
            return _response(chat_service.get_agent(workflow_id, agent_uid))
        except Exception as exc:
            return error_response(exc, _status_for(exc))

    @routes.get("/ryan/agent/context-summary")
    async def context_summary(request: Any) -> Any:
        try:
            workflow_id = str(request.query.get("workflow_id", ""))
            if not workflow_id:
                raise ValueError("workflow_id is required")
            raw = request.query.get("upstream_context")
            payload = json.loads(raw) if raw else {"workflow_id": workflow_id}
            if not isinstance(payload, Mapping):
                raise ValueError("upstream_context must be an object")
            if request.query.get("agent_uid"):
                result = commit_service.context_with_latest(
                    workflow_id, str(request.query["agent_uid"]), payload,
                )
            else:
                result = RyanContext.from_dict({**payload, "workflow_id": workflow_id})
            return _response({"status": "ok", "workflow_id": workflow_id, "entries": len(result.entries),
                              "assets": len(result.assets),
                              "entry_ids": [entry.entry_id for entry in result.entries]})
        except Exception as exc:
            return error_response(exc, _status_for(exc))

    async def run_chat(request: Any) -> Any:
        try:
            body = await _json_body(request)
            result = await asyncio.to_thread(chat_service.discuss, body)
            return _response(result)
        except Exception as exc:
            return error_response(exc, _status_for(exc))

    @routes.post("/ryan/agent/chat")
    async def chat(request: Any) -> Any:
        return await run_chat(request)

    @routes.post("/ryan/agent/chat/stream")
    async def chat_stream(request: Any) -> Any:
        # Event JSON is intentionally stable; the UI can consume the same list
        # over HTTP while ComfyUI websocket publishing remains optional.
        return await run_chat(request)

    @routes.post("/ryan/agent/commit")
    async def commit(request: Any) -> Any:
        try:
            body = await _json_body(request)
            return _response(await asyncio.to_thread(commit_service.commit, body))
        except Exception as exc:
            return error_response(exc, _status_for(exc))

    @routes.post("/ryan/agent/reset")
    async def reset(request: Any) -> Any:
        try:
            body = await _json_body(request)
            return _response(await asyncio.to_thread(chat_service.reset, str(body["workflow_id"]), str(body["agent_uid"])))
        except Exception as exc:
            return error_response(exc, _status_for(exc))

    @routes.post("/ryan/agent/stop")
    async def stop(request: Any) -> Any:
        try:
            body = await _json_body(request)
            return _response(await asyncio.to_thread(chat_service.stop, str(body["workflow_id"]), str(body["agent_uid"]), request_id=str(body.get("request_id", "")), message_id=str(body.get("message_id", ""))))
        except Exception as exc:
            return error_response(exc, _status_for(exc))

    @routes.post("/ryan/agent/assets")
    async def attach_asset(request: Any) -> Any:
        temporary_path: str | None = None
        try:
            body, temporary_path = await _asset_body(request)
            workflow_id = str(body.get("workflow_id", ""))
            agent_uid = str(body.get("agent_uid", ""))
            source_path = body.get("source_path")
            if not workflow_id or not agent_uid:
                raise ValueError("workflow_id and agent_uid are required")
            if not source_path:
                raise ValueError("source_path or multipart file is required")
            asset = await asyncio.to_thread(
                asset_store.attach,
                workflow_id,
                agent_uid,
                str(source_path),
                asset_type=body.get("asset_type"),
                created_by=body.get("created_by") or body.get("created_by_agent_uid"),
                source=str(body.get("source", "chat_upload")),
                mime_type=body.get("mime_type"),
                display_name=body.get("display_name"),
            )
            return _response({"status": "attached", "asset": asset.to_dict()})
        except Exception as exc:
            return error_response(exc, _status_for(exc))
        finally:
            if temporary_path:
                Path(temporary_path).unlink(missing_ok=True)

    @routes.get("/ryan/agent/workflows/{workflow_id}/agents/{agent_uid}/assets")
    async def list_assets(request: Any) -> Any:
        try:
            workflow_id = request.match_info["workflow_id"]
            agent_uid = request.match_info["agent_uid"]
            assets = await asyncio.to_thread(asset_store.list, workflow_id, agent_uid)
            return _response({"status": "ok", "assets": [asset.to_dict() for asset in assets]})
        except Exception as exc:
            return error_response(exc, _status_for(exc))

    @routes.delete("/ryan/agent/assets/{asset_id}")
    async def detach_asset(request: Any) -> Any:
        try:
            query = getattr(request, "query", {}) or {}
            body: dict[str, Any] = dict(query)
            if not body.get("workflow_id") or not body.get("agent_uid"):
                try:
                    payload = await request.json()
                except Exception:
                    payload = {}
                if isinstance(payload, Mapping):
                    body.update(payload)
            workflow_id, agent_uid = str(body.get("workflow_id", "")), str(body.get("agent_uid", ""))
            if not workflow_id or not agent_uid:
                raise ValueError("workflow_id and agent_uid are required")
            asset_id = str(request.match_info["asset_id"])
            detached = await asyncio.to_thread(asset_store.detach, workflow_id, agent_uid, asset_id)
            return _response({"status": "detached", "asset_id": detached})
        except Exception as exc:
            return error_response(exc, _status_for(exc))

    return {"chat_service": chat_service, "commit_service": commit_service, "asset_store": asset_store}


# Importing the module in a plain Python process is safe; in ComfyUI this adds
# the routes without requiring changes to top-level registration files.
try:  # pragma: no cover - server availability is environment-dependent
    register_routes()
except Exception:
    pass

__all__ = ["error_response", "list_skills", "register_routes"]
