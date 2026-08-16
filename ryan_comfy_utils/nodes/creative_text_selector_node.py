"""从创作项目固定目录选择文本，输出可直连执行节点的 STRING。"""
from __future__ import annotations

from typing import Any

from ..creative_workspace.project_repository import CreativeProjectRepository
from ..creative_workspace.stage_export import (
    StageExportError,
    list_project_documents,
    parse_items_markdown,
    select_document_or_item,
)
from ..creative_workspace.stage_service import CreativeStageService


class RyanCreativeTextSelector:
    """绑定显式 creative_project_id；items 必须选条目。"""

    @classmethod
    def INPUT_TYPES(cls) -> dict[str, Any]:
        return {
            "required": {
                "creative_project_id": ("STRING", {"default": ""}),
                "document_path": ("STRING", {"default": ""}),
            },
            "optional": {
                "item_id": ("STRING", {"default": ""}),
            },
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("text",)
    FUNCTION = "select"
    CATEGORY = "Ryan/Creative"

    def __init__(self) -> None:
        self._repository = CreativeProjectRepository()
        self._stage_service = CreativeStageService(self._repository)

    def select(
        self,
        creative_project_id: str,
        document_path: str,
        item_id: str = "",
    ) -> tuple[str]:
        project_id = (creative_project_id or "").strip()
        path = (document_path or "").strip()
        if not project_id:
            raise ValueError("creative_project_id is required")
        if not path:
            raise ValueError("document_path is required")
        if not self._repository.project_exists(project_id):
            raise FileNotFoundError(f"creative project not found: {project_id}")
        paths = self._repository.paths(project_id)
        try:
            selected = select_document_or_item(paths, path, item_id)
        except StageExportError as exc:
            raise ValueError(str(exc)) from exc
        stale = self._stage_service.stale_stages_for_document(project_id, path)
        text = selected["text"]
        if stale:
            # 不污染纯提示词正文；节点侧用 stderr 风格提示由 Comfy 日志可见
            print(
                f"[RyanCreativeTextSelector] warning: document may be STALE "
                f"stages={stale} path={path}"
            )
        return (text,)

    @classmethod
    def list_documents(cls, creative_project_id: str) -> list[dict[str, Any]]:
        repo = CreativeProjectRepository()
        if not repo.project_exists(creative_project_id):
            return []
        return list_project_documents(repo.paths(creative_project_id))

    @classmethod
    def list_items(cls, creative_project_id: str, document_path: str) -> list[dict[str, str]]:
        repo = CreativeProjectRepository()
        if not repo.project_exists(creative_project_id):
            return []
        from ..creative_workspace.stage_export import read_document_text

        text = read_document_text(repo.paths(creative_project_id), document_path)
        if not document_path.endswith(".items.md"):
            return []
        return [
            {"id": item.item_id, "label": item.label, "text": item.text}
            for item in parse_items_markdown(text)
        ]


__all__ = ["RyanCreativeTextSelector"]
