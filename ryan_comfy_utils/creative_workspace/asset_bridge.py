"""ComfyTV HTTP Asset Bridge；无 ComfyTV 时本地降级。"""
from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlparse
from urllib.request import Request, urlopen


class AssetBridgeError(RuntimeError):
    """资产桥接失败。"""


def _default_http_json(method: str, url: str, body: dict[str, Any] | None = None, timeout: float = 10.0) -> Any:
    data = None
    headers = {"Accept": "application/json"}
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = Request(url, data=data, headers=headers, method=method.upper())
    with urlopen(request, timeout=timeout) as response:  # noqa: S310 - local Comfy API
        raw = response.read().decode("utf-8")
        return json.loads(raw) if raw else {}


@dataclass(slots=True)
class CompiledAssetContext:
    text: str
    attachment_paths: list[str]


class ComfyTVAssetBridge:
    def __init__(
        self,
        *,
        base_url: str = "http://127.0.0.1:8188",
        http_json: Callable[..., Any] | None = None,
        output_root: str | Path | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.http_json = http_json or _default_http_json
        self.output_root = Path(output_root) if output_root else Path.cwd() / "output"

    def available(self) -> bool:
        try:
            payload = self.http_json("GET", f"{self.base_url}/comfytv/assets?category=all&limit=1")
            return isinstance(payload, dict) and "assets" in payload
        except Exception:
            return False

    def list_assets(self, *, category: str = "all", limit: int = 200, offset: int = 0) -> list[dict[str, Any]]:
        if not self.available():
            return []
        try:
            payload = self.http_json(
                "GET",
                f"{self.base_url}/comfytv/assets?category={category}&limit={limit}&offset={offset}",
            )
        except (HTTPError, URLError, TimeoutError, AssetBridgeError, ValueError, TypeError) as exc:
            raise AssetBridgeError(str(exc)) from exc
        assets = payload.get("assets") if isinstance(payload, dict) else None
        return list(assets) if isinstance(assets, list) else []

    def list_categories(self) -> list[dict[str, Any]]:
        if not self.available():
            return []
        payload = self.http_json("GET", f"{self.base_url}/comfytv/asset_categories")
        cats = payload.get("categories") if isinstance(payload, dict) else None
        return list(cats) if isinstance(cats, list) else []

    def make_ref(
        self,
        asset: dict[str, Any],
        *,
        semantic_role: str = "reference",
        usage: str = "reference",
    ) -> dict[str, Any]:
        return {
            "asset_ref_id": f"ref_{uuid.uuid4().hex}",
            "provider": "comfytv",
            "provider_asset_id": asset.get("id"),
            "media_type": asset.get("media_type") or "image",
            "display_name": asset.get("name") or "",
            "payload_url": asset.get("payload_url") or "",
            "semantic_role": semantic_role,
            "usage": usage,
            "metadata_snapshot": {
                "mime_type": asset.get("mime_type"),
                "width": asset.get("width"),
                "height": asset.get("height"),
                "size_bytes": asset.get("size_bytes"),
            },
        }

    def make_local_ref(
        self,
        path: str | Path,
        *,
        media_type: str = "image",
        display_name: str = "",
        semantic_role: str = "reference",
    ) -> dict[str, Any]:
        p = Path(path)
        return {
            "asset_ref_id": f"ref_{uuid.uuid4().hex}",
            "provider": "local",
            "provider_asset_id": None,
            "media_type": media_type,
            "display_name": display_name or p.name,
            "payload_url": str(p),
            "local_path": str(p),
            "semantic_role": semantic_role,
            "usage": "reference",
            "metadata_snapshot": {},
        }

    def resolve_local_path(self, ref: dict[str, Any]) -> str | None:
        if ref.get("provider") == "local" and ref.get("local_path"):
            path = Path(str(ref["local_path"]))
            return str(path) if path.is_file() else None
        url = str(ref.get("payload_url") or "")
        if not url:
            return None
        if url.startswith("/") or "://" not in url:
            # /view?filename=...&type=output
            parsed = urlparse(url if "://" in url else f"http://local{url}")
            qs = parse_qs(parsed.query)
            filename = (qs.get("filename") or [None])[0]
            type_name = (qs.get("type") or ["output"])[0] or "output"
            if not filename:
                return None
            # Comfy view files live under output/input/temp
            base = self.output_root
            if type_name == "input":
                candidate = base.parent / "input" / filename
            elif type_name == "temp":
                candidate = base.parent / "temp" / filename
            else:
                candidate = base / filename
            return str(candidate) if candidate.is_file() else None
        local = Path(url)
        return str(local) if local.is_file() else None

    def compile_refs(self, refs: list[dict[str, Any]], *, cache_dir: Path | None = None) -> CompiledAssetContext:
        blocks: list[str] = []
        attachments: list[str] = []
        for ref in refs:
            media = str(ref.get("media_type") or "image")
            name = ref.get("display_name") or ref.get("asset_ref_id")
            role = ref.get("semantic_role") or "reference"
            local = self.resolve_local_path(ref)
            meta = ref.get("metadata_snapshot") or {}
            if media == "image":
                if local:
                    attachments.append(local)
                    blocks.append(
                        f"[ASSET image role={role} name={name} path={local}]"
                    )
                else:
                    blocks.append(
                        f"[ASSET image role={role} name={name} url={ref.get('payload_url')} "
                        f"note=unresolved_local_path metadata={json.dumps(meta, ensure_ascii=False)}]"
                    )
            elif media == "video":
                blocks.append(
                    f"[ASSET video role={role} name={name} url={ref.get('payload_url')} "
                    f"metadata={json.dumps(meta, ensure_ascii=False)} "
                    f"note=v1_metadata_or_keyframes_only]"
                )
                # optional keyframe path if cache provided later
                if cache_dir and local:
                    blocks.append(f"[ASSET video_local_ref path={local}]")
            else:
                blocks.append(
                    f"[ASSET {media} role={role} name={name} url={ref.get('payload_url')} "
                    f"metadata={json.dumps(meta, ensure_ascii=False)}]"
                )
        return CompiledAssetContext(text="\n".join(blocks), attachment_paths=attachments)


__all__ = [
    "AssetBridgeError",
    "CompiledAssetContext",
    "ComfyTVAssetBridge",
]
