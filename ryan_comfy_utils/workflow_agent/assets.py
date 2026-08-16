"""Workflow Agent Session Asset Store。

资产先复制到当前 Agent scope，再把副本 URI 交给 Pi；外部路径只在导入阶段使用。
"""
from __future__ import annotations

import hashlib
import json
import mimetypes
import os
import shutil
import tempfile
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from .models import RyanAssetRef
from .repository import WorkflowAgentRepository


MAX_ASSET_BYTES = 20 * 1024 * 1024
MAX_CONTEXT_TEXT_CHARS = 100_000
TEXT_EXTENSIONS = {".txt", ".md", ".json", ".csv"}
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".tif", ".tiff"}
VIDEO_EXTENSIONS = {".mp4", ".mov", ".m4v", ".avi", ".mkv", ".webm"}
AUDIO_EXTENSIONS = {".mp3", ".wav", ".flac", ".aac", ".ogg", ".m4a"}


class AssetStoreError(ValueError):
    """资产输入、类型或处理失败。"""


class AssetNotFoundError(AssetStoreError):
    """资产不在指定 Agent scope 的索引中。"""


class WorkflowAgentAssetStore:
    """按 ``workflow_id + agent_uid`` 隔离并持久化 Session 资产。"""

    def __init__(self, repository: WorkflowAgentRepository | None = None) -> None:
        self.repository = repository or WorkflowAgentRepository()
        self._lock = threading.RLock()

    def attach(
        self,
        workflow_id: str,
        agent_uid: str,
        source_path: str | os.PathLike[str],
        *,
        asset_type: str | None = None,
        created_by: str | None = None,
        source: str = "chat_upload",
        mime_type: str | None = None,
        display_name: str | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> RyanAssetRef:
        """校验、复制并索引一个外部文件；重复内容返回已有稳定引用。"""
        paths = self.repository.scope_paths(workflow_id, agent_uid, create=True)
        source_file = self._validate_source(source_path)
        size = source_file.stat().st_size
        if size > MAX_ASSET_BYTES:
            raise AssetStoreError(f"asset exceeds maximum size of {MAX_ASSET_BYTES} bytes")
        suffix = source_file.suffix.lower()
        inferred_type, inferred_mime = self._infer_type(suffix, mime_type)
        normalized_type = (asset_type or inferred_type).strip().lower()
        if normalized_type == "audio" or (mime_type or inferred_mime).lower().startswith("audio/"):
            raise AssetStoreError("audio assets are disabled and are not consumed by the agent")
        if normalized_type not in {"image", "document", "text", "video", "other"}:
            raise AssetStoreError(f"unsupported asset type: {normalized_type}")
        final_mime = (mime_type or inferred_mime).strip().lower()
        if normalized_type in {"document", "text"} and suffix not in TEXT_EXTENSIONS:
            raise AssetStoreError("only .txt, .md, .json and .csv documents are supported")
        if normalized_type == "image" and suffix not in IMAGE_EXTENSIONS and not final_mime.startswith("image/"):
            raise AssetStoreError("unsupported image format")
        if normalized_type == "video" and suffix not in VIDEO_EXTENSIONS and not final_mime.startswith("video/"):
            raise AssetStoreError("unsupported video format")
        if normalized_type == "other":
            raise AssetStoreError("unsupported asset format")

        digest = self._sha256(source_file)
        asset_id = self._stable_asset_id(workflow_id, agent_uid, normalized_type, final_mime, digest)
        with self._lock:
            index = self._read_index(paths.assets)
            existing = index.get(asset_id)
            if existing is not None:
                return RyanAssetRef.from_dict(existing)
            destination = paths.assets / f"{asset_id}{suffix}"
            destination.parent.mkdir(parents=True, exist_ok=True)
            # copyfile 不保留外部软链接，Pi 只会看到 scope 内的普通副本。
            try:
                shutil.copyfile(source_file, destination)
                ref_metadata = dict(metadata or {})
                ref_metadata.update({
                    "sha256": digest,
                    "original_path": str(source_file),
                    "scope_agent_uid": paths.agent_uid,
                })
                ref = RyanAssetRef(
                    asset_id=asset_id,
                    workflow_id=paths.workflow_id,
                    type=normalized_type,
                    mime_type=final_mime,
                    display_name=Path(display_name or source_file.name).name or source_file.name,
                    source=str(source),
                    uri=str(destination),
                    size_bytes=size,
                    created_by_agent_uid=created_by or paths.agent_uid,
                    created_at=datetime.now(timezone.utc).isoformat(),
                    metadata=ref_metadata,
                )
                # 视频必须在索引提交前完成探测；失败时不留下“已附加但不可消费”的记录。
                if normalized_type == "video":
                    ref = self._attach_video_derivatives(ref, destination, index)
                index[asset_id] = ref.to_dict()
                self._write_index(paths.assets, index)
                return ref
            except Exception:
                destination.unlink(missing_ok=True)
                raise

    # Chat Upload / 节点输入可共用同一入口。
    attach_file = attach
    materialize = attach

    def list(
        self,
        workflow_id: str,
        agent_uid: str,
    ) -> list[RyanAssetRef]:
        paths = self.repository.scope_paths(workflow_id, agent_uid, create=False)
        with self._lock:
            records = self._read_index(paths.assets)
        return [RyanAssetRef.from_dict(records[key]) for key in sorted(records)]

    list_assets = list

    def get(self, workflow_id: str, agent_uid: str, asset_id: str) -> RyanAssetRef:
        paths = self.repository.scope_paths(workflow_id, agent_uid, create=False)
        with self._lock:
            record = self._read_index(paths.assets).get(asset_id)
        if record is None:
            raise AssetNotFoundError(f"asset not found: {asset_id}")
        return RyanAssetRef.from_dict(record)

    def detach(self, workflow_id: str, agent_uid: str, asset_id: str) -> str:
        """删除引用/索引，保留物理副本，避免共享稳定 ID 被误删。"""
        paths = self.repository.scope_paths(workflow_id, agent_uid, create=False)
        with self._lock:
            index = self._read_index(paths.assets)
            if asset_id not in index:
                raise AssetNotFoundError(f"asset not found: {asset_id}")
            del index[asset_id]
            self._write_index(paths.assets, index)
        return asset_id

    remove = detach

    def extract_text(
        self,
        asset: RyanAssetRef | str,
        workflow_id: str | None = None,
        agent_uid: str | None = None,
        *,
        max_chars: int = MAX_CONTEXT_TEXT_CHARS,
    ) -> dict[str, Any]:
        """提取文档文本，明确返回是否因 Context 上限截断。"""
        ref = self._resolve_ref(asset, workflow_id, agent_uid)
        if ref.type not in {"document", "text"} or Path(ref.display_name).suffix.lower() not in TEXT_EXTENSIONS:
            raise AssetStoreError("asset is not a supported text document")
        if max_chars < 0:
            raise ValueError("max_chars must not be negative")
        path = self._stored_path(ref)
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError as exc:
            raise AssetStoreError("text asset must be UTF-8") from exc
        truncated = len(text) > max_chars
        return {
            "asset_id": ref.asset_id,
            "text": text[:max_chars],
            "truncated": truncated,
            "original_chars": len(text),
            "max_chars": max_chars,
            "message": f"text truncated to {max_chars} characters" if truncated else "",
        }

    text_for_context = extract_text

    def prepare_context(
        self,
        workflow_id: str,
        agent_uid: str,
        assets: Any,
    ) -> dict[str, Any]:
        """把 AssetRef 与文档正文整理成 Pi 可消费的受限上下文。"""
        values = assets if isinstance(assets, (list, tuple)) else [assets]
        refs: list[dict[str, Any]] = []
        documents: list[dict[str, Any]] = []
        passthrough: list[Any] = []
        for value in values:
            candidate: RyanAssetRef | str | None = None
            if isinstance(value, RyanAssetRef):
                candidate = value
            elif isinstance(value, Mapping) and value.get("asset_id"):
                candidate = RyanAssetRef.from_dict(value)
            elif isinstance(value, str):
                candidate = value
            if candidate is None:
                passthrough.append(value)
                continue
            ref = self._resolve_ref(candidate, workflow_id, agent_uid)
            refs.append(ref.to_dict())
            if ref.type in {"document", "text"}:
                documents.append(self.extract_text(ref))
        return {"refs": refs, "documents": documents, "other": passthrough}

    def _resolve_ref(
        self,
        asset: RyanAssetRef | str,
        workflow_id: str | None,
        agent_uid: str | None,
    ) -> RyanAssetRef:
        if isinstance(asset, RyanAssetRef):
            ref = asset
            if workflow_id and ref.workflow_id != workflow_id:
                raise AssetStoreError("asset workflow mismatch")
            ref_scope_agent = str(ref.metadata.get("scope_agent_uid", "") or ref.created_by_agent_uid)
            resolved_workflow = workflow_id or ref.workflow_id
            resolved_agent = ref_scope_agent or agent_uid
            if not resolved_workflow or not resolved_agent:
                raise AssetStoreError("workflow_id and agent_uid are required to resolve an asset")
            return self.get(resolved_workflow, resolved_agent, ref.asset_id)
        if not workflow_id or not agent_uid:
            raise AssetStoreError("workflow_id and agent_uid are required to resolve an asset")
        return self.get(workflow_id, agent_uid, str(asset))

    def _stored_path(self, ref: RyanAssetRef) -> Path:
        scope_agent_uid = str(ref.metadata.get("scope_agent_uid", "") or ref.created_by_agent_uid)
        root = self.repository.assets_path(ref.workflow_id, scope_agent_uid, create=False).resolve()
        path = Path(ref.uri).resolve()
        try:
            path.relative_to(root)
        except ValueError as exc:
            raise AssetStoreError("asset URI escapes the Agent scope") from exc
        if not path.is_file():
            raise AssetNotFoundError(f"stored asset file is missing: {ref.asset_id}")
        return path

    @staticmethod
    def _validate_source(source_path: str | os.PathLike[str]) -> Path:
        try:
            raw = os.fspath(source_path)
        except TypeError as exc:
            raise AssetStoreError("source_path must be a filesystem path") from exc
        if "\x00" in raw:
            raise AssetStoreError("source_path contains an invalid null character")
        source = Path(raw)
        try:
            resolved = source.resolve(strict=True)
        except FileNotFoundError as exc:
            raise AssetStoreError(f"source file does not exist: {source}") from exc
        except OSError as exc:
            raise AssetStoreError(f"source path is invalid: {source}") from exc
        if not resolved.is_file():
            raise AssetStoreError(f"source path is not a regular file: {source}")
        return resolved

    @staticmethod
    def _infer_type(suffix: str, mime_type: str | None) -> tuple[str, str]:
        mime = (mime_type or mimetypes.guess_type(f"file{suffix}")[0] or "").lower()
        if suffix in TEXT_EXTENSIONS:
            return "document", mime or "text/plain"
        if suffix in IMAGE_EXTENSIONS or mime.startswith("image/"):
            return "image", mime or "application/octet-stream"
        if suffix in VIDEO_EXTENSIONS or mime.startswith("video/"):
            return "video", mime or "application/octet-stream"
        if suffix in AUDIO_EXTENSIONS or mime.startswith("audio/"):
            return "audio", mime or "application/octet-stream"
        return "other", mime or "application/octet-stream"

    @staticmethod
    def _sha256(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    @staticmethod
    def _stable_asset_id(workflow_id: str, agent_uid: str, asset_type: str, mime_type: str, digest: str) -> str:
        payload = "\0".join((workflow_id, agent_uid, asset_type, mime_type, digest)).encode("utf-8")
        return "asset_" + hashlib.sha256(payload).hexdigest()

    @staticmethod
    def _read_index(assets_dir: Path) -> dict[str, dict[str, Any]]:
        path = assets_dir / "index.json"
        if not path.exists():
            return {}
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise AssetStoreError(f"invalid asset index: {path}") from exc
        if not isinstance(payload, dict) or not isinstance(payload.get("assets", {}), dict):
            raise AssetStoreError("asset index must contain an assets object")
        return {str(key): value for key, value in payload["assets"].items() if isinstance(value, dict)}

    @staticmethod
    def _write_index(assets_dir: Path, records: Mapping[str, Mapping[str, Any]]) -> None:
        assets_dir.mkdir(parents=True, exist_ok=True)
        path = assets_dir / "index.json"
        temporary = assets_dir / f".index-{os.getpid()}-{threading.get_ident()}.tmp"
        temporary.write_text(json.dumps({"assets": records}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        temporary.replace(path)

    def _attach_video_derivatives(
        self,
        ref: RyanAssetRef,
        copied_path: Path,
        records: dict[str, dict[str, Any]],
    ) -> RyanAssetRef:
        try:
            import cv2  # type: ignore
        except Exception as exc:
            raise AssetStoreError("video dependency unavailable: install OpenCV to extract video frames") from exc
        capture = cv2.VideoCapture(str(copied_path))
        try:
            if not capture.isOpened():
                raise AssetStoreError("video has no valid readable frames")
            frame_count = int(capture.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
            fps = float(capture.get(cv2.CAP_PROP_FPS) or 0)
            width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
            height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
            indices = sorted({0, max(0, frame_count // 2), max(0, frame_count - 1)})
            derived: list[dict[str, Any]] = []
            for frame_index in indices[:3]:
                capture.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
                ok, frame = capture.read()
                if not ok or frame is None:
                    continue
                with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as temporary:
                    frame_path = Path(temporary.name)
                try:
                    if not cv2.imwrite(str(frame_path), frame):
                        continue
                    frame_ref = self.attach(
                        ref.workflow_id,
                        ref.created_by_agent_uid,
                        frame_path,
                        asset_type="image",
                        created_by=ref.created_by_agent_uid,
                        source="video_scene_first_frame" if frame_index == 0 else "video_keyframe",
                        metadata={"parent_asset_id": ref.asset_id, "frame_index": frame_index},
                    )
                    records[frame_ref.asset_id] = frame_ref.to_dict()
                    derived.append(frame_ref.to_dict())
                finally:
                    frame_path.unlink(missing_ok=True)
            if not derived:
                raise AssetStoreError("video has no valid readable frames")
            metadata = dict(ref.metadata)
            metadata.update({
                "video": {"frame_count": frame_count, "fps": fps, "width": width, "height": height},
                "derived_assets": derived,
            })
            return RyanAssetRef.from_dict({**ref.to_dict(), "metadata": metadata})
        finally:
            capture.release()


# 兼容调用侧可能采用的名称。
AssetStore = WorkflowAgentAssetStore
AgentAssetStore = WorkflowAgentAssetStore

__all__ = [
    "AgentAssetStore",
    "AssetNotFoundError",
    "AssetStore",
    "AssetStoreError",
    "MAX_ASSET_BYTES",
    "MAX_CONTEXT_TEXT_CHARS",
    "WorkflowAgentAssetStore",
]
