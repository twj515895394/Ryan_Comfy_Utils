"""Creative Workspace HTTP API；无 ComfyUI 时可安全导入。"""
from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any, Mapping

from .asset_bridge import AssetBridgeError, ComfyTVAssetBridge
from .chat_service import CreativeChatError, CreativeChatService
from .project_repository import CreativeProjectRepository
from .stage_export import StageExportError, list_project_documents, select_document_or_item
from .stage_registry import list_stage_skills, load_pipeline
from .stage_service import CreativeStageService, StageServiceError

try:
    from aiohttp import web  # type: ignore
except Exception:  # pragma: no cover
    web = None  # type: ignore


def _response(payload: Mapping[str, Any], status: int = 200) -> Any:
    if web is not None:
        return web.json_response(dict(payload), status=status)
    return dict(payload)


def _error(exc: Exception, status: int = 400) -> Any:
    return _response({"status": "error", "error": str(exc) or "request failed"}, status)


def _status_for(exc: Exception) -> int:
    if isinstance(exc, FileNotFoundError):
        return 404
    if isinstance(
        exc,
        (
            CreativeChatError,
            StageServiceError,
            StageExportError,
            AssetBridgeError,
            ValueError,
            TypeError,
            KeyError,
        ),
    ):
        return 400
    return 500


async def _json_body(request: Any) -> dict[str, Any]:
    payload = await request.json()
    if not isinstance(payload, dict):
        raise ValueError("json body must be an object")
    return payload


def build_services(
    repository: CreativeProjectRepository | None = None,
    rpc_runner: Any | None = None,
    *,
    event_publisher: Any | None = None,
    prompt_server: Any | None = None,
) -> dict[str, Any]:
    repo = repository or CreativeProjectRepository()
    publisher = event_publisher
    if publisher is None and prompt_server is not None:
        send_sync = getattr(prompt_server, "send_sync", None)
        if callable(send_sync):
            def publish_creative_event(event: dict[str, Any]) -> None:
                payload = dict(event)
                payload.setdefault("channel", "creative")
                try:
                    send_sync("ryan_creative_event", payload, getattr(prompt_server, "client_id", None))
                except TypeError:
                    send_sync("ryan_creative_event", payload)

            publisher = publish_creative_event
    chat = CreativeChatService(repo, rpc_runner=rpc_runner, event_publisher=publisher)
    stage = CreativeStageService(repo, commit_runner=chat.commit_text_via_runner)
    chat.stage_service = stage
    bridge = ComfyTVAssetBridge(
        output_root=repo.root.parent if repo.root.name == "ryan_creative_workspace" else None
    )
    return {
        "repository": repo,
        "chat_service": chat,
        "stage_service": stage,
        "asset_bridge": bridge,
    }


def register_routes(
    routes: Any | None = None,
    *,
    repository: CreativeProjectRepository | None = None,
    rpc_runner: Any | None = None,
) -> dict[str, Any]:
    prompt_server = None
    app_routes = routes
    if app_routes is None:
        try:
            from server import PromptServer  # type: ignore

            prompt_server = getattr(PromptServer, "instance", None)
            app_routes = getattr(prompt_server, "routes", None) if prompt_server is not None else None
        except Exception:
            prompt_server = None
            app_routes = None

    services = build_services(
        repository=repository,
        rpc_runner=rpc_runner,
        prompt_server=prompt_server,
    )
    repo: CreativeProjectRepository = services["repository"]
    chat: CreativeChatService = services["chat_service"]
    stage_service: CreativeStageService = services["stage_service"]
    bridge: ComfyTVAssetBridge = services["asset_bridge"]

    if web is None or app_routes is None:
        return services

    @app_routes.get("/ryan/creative/projects")
    async def list_projects(request: Any) -> Any:
        try:
            current = repo.get_current_project_id()
            return _response(
                {
                    "status": "ok",
                    "current_creative_project_id": current,
                    "projects": repo.list_projects(),
                }
            )
        except Exception as exc:  # noqa: BLE001
            return _error(exc, _status_for(exc))

    @app_routes.post("/ryan/creative/projects")
    async def create_project(request: Any) -> Any:
        try:
            body = await _json_body(request)
            project = repo.create_project(name=str(body.get("name") or ""))
            return _response({"status": "ok", "project": project})
        except Exception as exc:  # noqa: BLE001
            return _error(exc, _status_for(exc))

    @app_routes.post("/ryan/creative/workspace/reset")
    async def reset_workspace(request: Any) -> Any:
        try:
            body = {}
            if request.can_read_body:
                try:
                    body = await _json_body(request)
                except Exception:
                    body = {}
            project = repo.reset_workspace(name=str(body.get("name") or "新工作区"))
            return _response({"status": "ok", "project": project})
        except Exception as exc:  # noqa: BLE001
            return _error(exc, _status_for(exc))

    @app_routes.get("/ryan/creative/projects/{project_id}")
    async def get_project(request: Any) -> Any:
        try:
            project_id = request.match_info["project_id"]
            project = repo.open_project(project_id)
            return _response({"status": "ok", "project": project})
        except Exception as exc:  # noqa: BLE001
            return _error(exc, _status_for(exc))

    @app_routes.get("/ryan/creative/projects/{project_id}/stages")
    async def get_stages(request: Any) -> Any:
        try:
            project_id = request.match_info["project_id"]
            return _response({"status": "ok", "stages": stage_service.list_stages(project_id)})
        except Exception as exc:  # noqa: BLE001
            return _error(exc, _status_for(exc))

    @app_routes.post("/ryan/creative/projects/{project_id}/stages/{stage_id}/confirm")
    async def confirm_stage(request: Any) -> Any:
        try:
            project_id = request.match_info["project_id"]
            stage_id = request.match_info["stage_id"]
            body = await _json_body(request)
            result = stage_service.confirm(
                project_id,
                stage_id,
                thread_id=str(body.get("thread_id") or ""),
                mode=str(body.get("mode") or "commit"),
                user_message=str(body.get("message") or ""),
            )
            return _response(result)
        except Exception as exc:  # noqa: BLE001
            return _error(exc, _status_for(exc))

    @app_routes.post("/ryan/creative/projects/{project_id}/stages/{stage_id}/reopen")
    async def reopen_stage(request: Any) -> Any:
        try:
            project_id = request.match_info["project_id"]
            stage_id = request.match_info["stage_id"]
            stage = stage_service.reopen(project_id, stage_id)
            return _response({"status": "ok", "stage": stage})
        except Exception as exc:  # noqa: BLE001
            return _error(exc, _status_for(exc))

    @app_routes.get("/ryan/creative/projects/{project_id}/stages/{stage_id}/ready")
    async def ready_stage(request: Any) -> Any:
        try:
            project_id = request.match_info["project_id"]
            stage_id = request.match_info["stage_id"]
            thread_id = request.rel_url.query.get("thread_id", "")
            return _response(
                {"status": "ok", **stage_service.evaluate_ready(project_id, stage_id, thread_id)}
            )
        except Exception as exc:  # noqa: BLE001
            return _error(exc, _status_for(exc))

    @app_routes.post("/ryan/creative/chat")
    async def creative_chat(request: Any) -> Any:
        try:
            body = await _json_body(request)

            def _run() -> dict[str, Any]:
                return chat.discuss(
                    project_id=str(body.get("project_id") or ""),
                    stage_id=str(body.get("stage_id") or ""),
                    message=str(body.get("message") or ""),
                    thread_id=str(body.get("thread_id") or ""),
                    skill_id=str(body.get("skill_id") or ""),
                    skill_scope=str(body.get("skill_scope") or "stage"),
                    asset_ref_ids=list(body.get("asset_ref_ids") or []),
                )

            result = await asyncio.to_thread(_run)
            return _response({"status": "ok", **result})
        except Exception as exc:  # noqa: BLE001
            return _error(exc, _status_for(exc))

    @app_routes.post("/ryan/creative/chat/stop")
    async def creative_chat_stop(request: Any) -> Any:
        try:
            body = await _json_body(request)
            result = chat.stop(
                project_id=str(body.get("project_id") or ""),
                thread_id=str(body.get("thread_id") or ""),
            )
            return _response({"status": "ok", **result})
        except Exception as exc:  # noqa: BLE001
            return _error(exc, _status_for(exc))

    @app_routes.get("/ryan/creative/projects/{project_id}/stages/{stage_id}/threads/{thread_id}/messages")
    async def thread_messages(request: Any) -> Any:
        try:
            project_id = request.match_info["project_id"]
            stage_id = request.match_info["stage_id"]
            thread_id = request.match_info["thread_id"]
            records = repo.read_thread_records(project_id, stage_id, thread_id)
            messages = [
                {
                    "role": r.get("role") or "assistant",
                    "content": r.get("content") or "",
                    "status": r.get("status") or "",
                    "message_id": r.get("message_id") or "",
                    "request_id": r.get("request_id") or "",
                    "error": r.get("error") or "",
                    "skill_id": r.get("skill_id") or "",
                }
                for r in records
                if r.get("role") in {"user", "assistant", "system"}
            ]
            return _response(
                {
                    "status": "ok",
                    "project_id": project_id,
                    "stage_id": stage_id,
                    "thread_id": thread_id,
                    "messages": messages,
                }
            )
        except Exception as exc:  # noqa: BLE001
            return _error(exc, _status_for(exc))

    @app_routes.get("/ryan/creative/skills")
    async def creative_skills(request: Any) -> Any:
        try:
            return _response(
                {
                    "status": "ok",
                    "pipeline": load_pipeline().to_public_dict(),
                    "skills": list_stage_skills(),
                }
            )
        except Exception as exc:  # noqa: BLE001
            return _error(exc, _status_for(exc))

    @app_routes.get("/ryan/creative/projects/{project_id}/documents")
    async def project_documents(request: Any) -> Any:
        try:
            project_id = request.match_info["project_id"]
            docs = list_project_documents(repo.paths(project_id))
            # annotate stale
            for doc in docs:
                stale_stages = stage_service.stale_stages_for_document(project_id, doc["path"])
                doc["stale"] = bool(stale_stages)
                doc["stale_stages"] = stale_stages
            return _response({"status": "ok", "documents": docs})
        except Exception as exc:  # noqa: BLE001
            return _error(exc, _status_for(exc))

    @app_routes.get("/ryan/creative/projects/{project_id}/documents/select")
    async def select_document(request: Any) -> Any:
        try:
            project_id = request.match_info["project_id"]
            path = request.rel_url.query.get("path", "")
            item_id = request.rel_url.query.get("item_id", "")
            selected = select_document_or_item(repo.paths(project_id), path, item_id)
            stale_stages = stage_service.stale_stages_for_document(project_id, path)
            selected["stale"] = bool(stale_stages)
            selected["stale_stages"] = stale_stages
            selected["stale_hint"] = bool(stale_stages)
            return _response({"status": "ok", "selection": selected})
        except Exception as exc:  # noqa: BLE001
            return _error(exc, _status_for(exc))

    @app_routes.get("/ryan/creative/assets/providers")
    async def asset_providers(request: Any) -> Any:
        try:
            comfy = await asyncio.to_thread(bridge.available)
            return _response(
                {
                    "status": "ok",
                    "providers": [
                        {"id": "comfytv", "available": comfy},
                        {"id": "local", "available": True},
                    ],
                }
            )
        except Exception as exc:  # noqa: BLE001
            return _error(exc, _status_for(exc))

    @app_routes.get("/ryan/creative/assets")
    async def list_assets(request: Any) -> Any:
        try:
            provider = request.rel_url.query.get("provider", "comfytv")
            if provider == "local":
                return _response({"status": "ok", "assets": []})
            if provider != "comfytv":
                return _response({"status": "ok", "assets": []})

            def _list() -> list[dict[str, Any]]:
                try:
                    return bridge.list_assets(
                        category=request.rel_url.query.get("category", "all"),
                        limit=int(request.rel_url.query.get("limit", "200")),
                        offset=int(request.rel_url.query.get("offset", "0")),
                    )
                except Exception:
                    return []

            assets = await asyncio.to_thread(_list)
            return _response({"status": "ok", "assets": assets})
        except Exception as exc:  # noqa: BLE001
            return _error(exc, _status_for(exc))

    @app_routes.post("/ryan/creative/projects/{project_id}/asset-refs")
    async def add_asset_ref(request: Any) -> Any:
        try:
            project_id = request.match_info["project_id"]
            body = await _json_body(request)
            refs = repo.read_asset_refs(project_id)
            if body.get("provider") == "local":
                ref = bridge.make_local_ref(
                    body.get("path") or body.get("local_path") or "",
                    media_type=str(body.get("media_type") or "image"),
                    display_name=str(body.get("display_name") or ""),
                    semantic_role=str(body.get("semantic_role") or "reference"),
                )
            else:
                asset = body.get("asset") if isinstance(body.get("asset"), dict) else body
                ref = bridge.make_ref(
                    asset,
                    semantic_role=str(body.get("semantic_role") or "reference"),
                    usage=str(body.get("usage") or "reference"),
                )
            refs.append(ref)
            repo.write_asset_refs(project_id, refs)
            return _response({"status": "ok", "asset_ref": ref, "asset_refs": refs})
        except Exception as exc:  # noqa: BLE001
            return _error(exc, _status_for(exc))

    @app_routes.post("/ryan/creative/projects/{project_id}/local-assets")
    async def upload_local_asset(request: Any) -> Any:
        """Upload local image/video/audio into project cache and create AssetRef."""
        try:
            project_id = request.match_info["project_id"]
            if web is None:
                raise RuntimeError("aiohttp unavailable")
            reader = await request.multipart()
            filename = "upload.bin"
            media_type = ""
            payload = b""
            while True:
                part = await reader.next()
                if part is None:
                    break
                name = part.name or ""
                if name in {"file", "upload", "asset"}:
                    filename = part.filename or filename
                    payload = await part.read(decode=False)
                elif name == "media_type":
                    media_type = (await part.text()).strip()
                elif name == "filename":
                    filename = (await part.text()).strip() or filename
            if not payload:
                # also accept raw body fallback
                raw = await request.read()
                if raw:
                    payload = raw
            if not payload:
                raise ValueError("empty upload")
            uploads_dir = repo.paths(project_id).cache / "uploads"
            ref = bridge.save_local_upload(
                project_uploads_dir=uploads_dir,
                filename=filename,
                data=payload,
                media_type=media_type,
            )
            refs = repo.read_asset_refs(project_id)
            refs.append(ref)
            repo.write_asset_refs(project_id, refs)
            return _response({"status": "ok", "asset_ref": ref, "asset_refs": refs})
        except Exception as exc:  # noqa: BLE001
            return _error(exc, _status_for(exc))

    @app_routes.get("/ryan/creative/projects/{project_id}/threads")
    async def list_threads(request: Any) -> Any:
        try:
            project_id = request.match_info["project_id"]
            state = repo.read_state(project_id)
            return _response({"status": "ok", "threads": state.get("threads") or {}})
        except Exception as exc:  # noqa: BLE001
            return _error(exc, _status_for(exc))

    @app_routes.post("/ryan/creative/projects/{project_id}/stages/{stage_id}/threads")
    async def create_thread(request: Any) -> Any:
        try:
            project_id = request.match_info["project_id"]
            stage_id = request.match_info["stage_id"]
            body = await _json_body(request)
            thread = repo.create_thread(project_id, stage_id, title=str(body.get("title") or ""))
            return _response({"status": "ok", "thread": thread})
        except Exception as exc:  # noqa: BLE001
            return _error(exc, _status_for(exc))

    return services


try:  # pragma: no cover
    register_routes()
except Exception:
    pass


__all__ = ["build_services", "register_routes"]
