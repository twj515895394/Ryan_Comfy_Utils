"""ryan-stage-export 解析与 canon/deliverables 落盘。"""
from __future__ import annotations

import json
import re
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .project_repository import CreativeProjectRepository, ProjectPaths
from .stage_registry import DeliverableSpec, StageSpec, load_pipeline

_EXPORT_BLOCK = re.compile(
    r"```ryan-stage-export(?:[ \t]+)?\r?\n(.*?)\r?\n?```",
    re.DOTALL,
)
_ITEM_HEADING = re.compile(r"^##\s+(\S+)\s*[—-]\s*(.+?)\s*$")


class StageExportError(ValueError):
    """导出结构不符合合同。"""


@dataclass(frozen=True, slots=True)
class ExportItem:
    item_id: str
    label: str
    text: str


@dataclass(frozen=True, slots=True)
class ExportDeliverable:
    doc_key: str
    format: str
    text: str = ""
    items: tuple[ExportItem, ...] = ()


@dataclass(frozen=True, slots=True)
class StageExportPayload:
    stage_id: str
    canon_markdown: str
    deliverables: tuple[ExportDeliverable, ...]


@dataclass(frozen=True, slots=True)
class ReadyCheck:
    ready: bool
    reason: str = ""
    payload: StageExportPayload | None = None


def extract_export_block(text: str) -> str | None:
    matches = list(_EXPORT_BLOCK.finditer(text or ""))
    if not matches:
        return None
    if len(matches) > 1:
        raise StageExportError("multiple ryan-stage-export blocks")
    return matches[0].group(1).strip()


def parse_stage_export(text: str) -> StageExportPayload:
    raw = extract_export_block(text)
    if raw is None:
        raise StageExportError("missing ryan-stage-export block")
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise StageExportError(f"invalid ryan-stage-export json: {exc}") from exc
    if not isinstance(data, dict):
        raise StageExportError("ryan-stage-export must be an object")
    stage_id = str(data.get("stage_id") or "").strip()
    if not stage_id:
        raise StageExportError("stage_id is required")
    canon = data.get("canon_markdown")
    if not isinstance(canon, str) or not canon.strip():
        raise StageExportError("canon_markdown must be a non-empty string")
    deliverables_raw = data.get("deliverables")
    if deliverables_raw is None:
        deliverables_raw = []
    if not isinstance(deliverables_raw, list):
        raise StageExportError("deliverables must be an array")
    deliverables: list[ExportDeliverable] = []
    for index, item in enumerate(deliverables_raw):
        if not isinstance(item, dict):
            raise StageExportError(f"deliverables[{index}] must be an object")
        doc_key = str(item.get("doc_key") or "").strip()
        fmt = str(item.get("format") or "doc").strip()
        if not doc_key:
            raise StageExportError(f"deliverables[{index}].doc_key is required")
        if fmt not in {"doc", "items"}:
            raise StageExportError(f"deliverables[{index}].format must be doc|items")
        if fmt == "doc":
            body = item.get("text")
            if not isinstance(body, str):
                raise StageExportError(f"deliverables[{index}].text must be a string")
            deliverables.append(ExportDeliverable(doc_key=doc_key, format=fmt, text=body))
            continue
        items_raw = item.get("items")
        if not isinstance(items_raw, list):
            raise StageExportError(f"deliverables[{index}].items must be an array")
        items: list[ExportItem] = []
        seen: set[str] = set()
        for j, row in enumerate(items_raw):
            if not isinstance(row, dict):
                raise StageExportError(f"deliverables[{index}].items[{j}] must be an object")
            item_id = str(row.get("id") or "").strip()
            label = str(row.get("label") or item_id).strip()
            text_body = row.get("text")
            if not item_id:
                raise StageExportError(f"deliverables[{index}].items[{j}].id is required")
            if item_id in seen:
                raise StageExportError(f"duplicate item id: {item_id}")
            if not isinstance(text_body, str) or not text_body.strip():
                raise StageExportError(f"deliverables[{index}].items[{j}].text must be non-empty")
            # 纯提示词：拒绝整段再包一层 fence/json 的明显污染可留给选择器；此处要求非空字符串
            seen.add(item_id)
            items.append(ExportItem(item_id=item_id, label=label or item_id, text=text_body.strip()))
        deliverables.append(
            ExportDeliverable(doc_key=doc_key, format=fmt, items=tuple(items))
        )
    return StageExportPayload(
        stage_id=stage_id,
        canon_markdown=canon.strip() + ("\n" if not canon.endswith("\n") else ""),
        deliverables=tuple(deliverables),
    )


def _render_items_markdown(items: tuple[ExportItem, ...] | list[ExportItem]) -> str:
    chunks: list[str] = []
    for item in items:
        chunks.append(f"## {item.item_id} — {item.label}\n\n{item.text.strip()}\n")
    return "\n".join(chunks).rstrip() + ("\n" if items else "")


def parse_items_markdown(text: str) -> list[ExportItem]:
    lines = (text or "").splitlines()
    items: list[ExportItem] = []
    current_id = ""
    current_label = ""
    body: list[str] = []

    def flush() -> None:
        nonlocal current_id, current_label, body
        if not current_id:
            return
        items.append(
            ExportItem(
                item_id=current_id,
                label=current_label or current_id,
                text="\n".join(body).strip(),
            )
        )
        current_id = ""
        current_label = ""
        body = []

    for line in lines:
        match = _ITEM_HEADING.match(line.strip())
        if match:
            flush()
            current_id = match.group(1).strip()
            current_label = match.group(2).strip()
            continue
        if current_id:
            body.append(line)
    flush()
    return [item for item in items if item.text]


def check_ready(text: str, stage: StageSpec) -> ReadyCheck:
    try:
        payload = parse_stage_export(text)
    except StageExportError as exc:
        return ReadyCheck(ready=False, reason=str(exc))
    if payload.stage_id != stage.stage_id:
        return ReadyCheck(
            ready=False,
            reason=f"export stage_id {payload.stage_id!r} != {stage.stage_id!r}",
        )
    by_key = {item.doc_key: item for item in payload.deliverables}
    for spec in stage.required_deliverables():
        found = by_key.get(spec.doc_key)
        if found is None:
            return ReadyCheck(ready=False, reason=f"missing required deliverable: {spec.doc_key}")
        if found.format != spec.format:
            return ReadyCheck(
                ready=False,
                reason=f"deliverable {spec.doc_key} format must be {spec.format}",
            )
        if spec.format == "items" and not found.items:
            return ReadyCheck(ready=False, reason=f"required items empty: {spec.doc_key}")
        if spec.format == "doc" and not str(found.text or "").strip():
            return ReadyCheck(ready=False, reason=f"required doc empty: {spec.doc_key}")
    return ReadyCheck(ready=True, payload=payload)


def _backup_file(path: Path, history_dir: Path, revision: int) -> None:
    if not path.is_file():
        return
    history_dir.mkdir(parents=True, exist_ok=True)
    target = history_dir / f"v{revision:03d}{path.suffix if path.suffix else '.md'}"
    if path.name.endswith(".items.md"):
        target = history_dir / f"v{revision:03d}.items.md"
    elif path.name == "latest.md":
        target = history_dir / f"v{revision:03d}.md"
    shutil.copy2(path, target)


def write_stage_export(
    repository: CreativeProjectRepository,
    project_id: str,
    stage_id: str,
    payload: StageExportPayload,
    *,
    revision: int,
) -> dict[str, Any]:
    if payload.stage_id != stage_id:
        raise StageExportError("payload stage_id mismatch")
    pipeline = load_pipeline()
    stage = pipeline.stage(stage_id)
    ready = check_ready(_synthetic_export_text(payload), stage)
    if not ready.ready or ready.payload is None:
        raise StageExportError(ready.reason or "export not ready")

    paths = repository.paths(project_id)
    canon_dir = paths.stage_canon_dir(stage_id)
    deliv_dir = paths.stage_deliverables_dir(stage_id)
    canon_dir.mkdir(parents=True, exist_ok=True)
    deliv_dir.mkdir(parents=True, exist_ok=True)
    canon_history = canon_dir / "history"
    deliv_history = deliv_dir / "history"

    latest = canon_dir / "latest.md"
    _backup_file(latest, canon_history, max(revision - 1, 0) or revision)
    # also keep vNNN at stage root for PRD friendliness
    versioned = canon_dir / f"v{revision:03d}.md"
    latest.write_text(payload.canon_markdown if payload.canon_markdown.endswith("\n") else payload.canon_markdown + "\n", encoding="utf-8")
    versioned.write_text(latest.read_text(encoding="utf-8"), encoding="utf-8")

    written: list[str] = [str(latest.relative_to(paths.root)).replace("\\", "/")]
    by_key = {item.doc_key: item for item in payload.deliverables}
    # overwrite known main deliverable files for this stage contract
    for spec in stage.deliverables:
        target = deliv_dir / spec.filename()
        found = by_key.get(spec.doc_key)
        if found is None:
            if target.is_file():
                _backup_file(target, deliv_history, max(revision - 1, 0) or revision)
                target.unlink()
            continue
        _backup_file(target, deliv_history, max(revision - 1, 0) or revision)
        if found.format == "items":
            content = _render_items_markdown(found.items)
        else:
            content = (found.text or "").rstrip() + "\n"
        target.write_text(content, encoding="utf-8")
        written.append(str(target.relative_to(paths.root)).replace("\\", "/"))

    # also write any extra deliverables present in payload
    for found in payload.deliverables:
        if any(spec.doc_key == found.doc_key for spec in stage.deliverables):
            continue
        filename = f"{found.doc_key}.items.md" if found.format == "items" else f"{found.doc_key}.md"
        target = deliv_dir / filename
        _backup_file(target, deliv_history, max(revision - 1, 0) or revision)
        if found.format == "items":
            target.write_text(_render_items_markdown(found.items), encoding="utf-8")
        else:
            target.write_text((found.text or "").rstrip() + "\n", encoding="utf-8")
        written.append(str(target.relative_to(paths.root)).replace("\\", "/"))

    return {
        "project_id": project_id,
        "stage_id": stage_id,
        "revision": revision,
        "written": written,
    }


def _synthetic_export_text(payload: StageExportPayload) -> str:
    body = {
        "stage_id": payload.stage_id,
        "canon_markdown": payload.canon_markdown,
        "deliverables": [
            (
                {
                    "doc_key": d.doc_key,
                    "format": d.format,
                    "items": [
                        {"id": i.item_id, "label": i.label, "text": i.text}
                        for i in d.items
                    ],
                }
                if d.format == "items"
                else {"doc_key": d.doc_key, "format": d.format, "text": d.text}
            )
            for d in payload.deliverables
        ],
    }
    return f"```ryan-stage-export\n{json.dumps(body, ensure_ascii=False)}\n```"


def list_project_documents(paths: ProjectPaths) -> list[dict[str, Any]]:
    """选择器文档清单：canon/**/latest.md + deliverables/**/*.md"""
    docs: list[dict[str, Any]] = []
    root = paths.root

    def add(path: Path, kind: str) -> None:
        if not path.is_file():
            return
        rel = path.relative_to(root).as_posix()
        docs.append(
            {
                "path": rel,
                "kind": kind,
                "name": path.name,
                "is_items": path.name.endswith(".items.md"),
            }
        )

    if paths.canon.is_dir():
        for latest in sorted(paths.canon.glob("*/latest.md")):
            add(latest, "canon")
    if paths.deliverables.is_dir():
        for path in sorted(paths.deliverables.rglob("*.md")):
            if "history" in path.parts:
                continue
            add(path, "deliverable")
    return docs


def read_document_text(paths: ProjectPaths, relative_path: str) -> str:
    rel = (relative_path or "").replace("\\", "/").lstrip("/")
    if not rel or ".." in rel.split("/"):
        raise StageExportError("invalid document path")
    path = (paths.root / rel).resolve()
    root = paths.root.resolve()
    if root not in path.parents and path != root:
        # allow file under root
        try:
            path.relative_to(root)
        except ValueError as exc:
            raise StageExportError("document path escapes project") from exc
    if not path.is_file():
        raise FileNotFoundError(relative_path)
    return path.read_text(encoding="utf-8")


def select_document_or_item(
    paths: ProjectPaths,
    relative_path: str,
    item_id: str = "",
) -> dict[str, Any]:
    text = read_document_text(paths, relative_path)
    is_items = relative_path.replace("\\", "/").endswith(".items.md")
    if is_items:
        if not str(item_id or "").strip():
            raise StageExportError("items document requires item_id")
        items = parse_items_markdown(text)
        for item in items:
            if item.item_id == item_id:
                return {
                    "path": relative_path.replace("\\", "/"),
                    "item_id": item.item_id,
                    "label": item.label,
                    "text": item.text,
                    "stale_hint": False,
                }
        raise FileNotFoundError(f"item not found: {item_id}")
    return {
        "path": relative_path.replace("\\", "/"),
        "item_id": "",
        "label": Path(relative_path).name,
        "text": text,
        "stale_hint": False,
    }


__all__ = [
    "StageExportError",
    "ExportItem",
    "ExportDeliverable",
    "StageExportPayload",
    "ReadyCheck",
    "extract_export_block",
    "parse_stage_export",
    "parse_items_markdown",
    "check_ready",
    "write_stage_export",
    "list_project_documents",
    "read_document_text",
    "select_document_or_item",
]
