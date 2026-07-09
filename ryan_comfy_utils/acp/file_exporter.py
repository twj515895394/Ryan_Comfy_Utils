"""将 ACP 节点产出的 prompt 写入 ComfyUI output 下固定子目录。"""

from datetime import datetime, timezone
from pathlib import Path

from .path_safety import resolve_under_root, sanitize_path_component, sanitize_relative_subdir


NODE_SLUG_IMAGE_ANALYZE = "image_analyze"
NODE_SLUG_IMAGE_PROMPT = "image_prompt"
NODE_SLUG_VIDEO_PROMPT = "video_prompt"
NODE_SLUG_FILE_GENERATOR = "file_generator"

EXPORT_SUBDIR = "ryan_acp_exports"


def resolve_comfy_output_root() -> Path:
    """优先 ComfyUI folder_paths，否则 cwd/output（便于单测）。"""
    try:
        import folder_paths  # type: ignore

        return Path(folder_paths.get_output_directory())
    except Exception:
        return Path.cwd() / "output"


def build_export_path(
    output_root: Path,
    node_slug: str,
    session_id: str,
    export_filename: str = "",
) -> Path:
    safe_slug = sanitize_path_component(node_slug, field="node_slug")
    directory = resolve_under_root(output_root, EXPORT_SUBDIR, safe_slug)
    directory.mkdir(parents=True, exist_ok=True)
    name = (export_filename or "").strip()
    if name:
        # 只取 basename，防止用户传入带路径的 export_filename
        stem = Path(name).name
        if stem.endswith(".md"):
            stem = stem[:-3]
        stem = sanitize_path_component(stem, field="export_filename")
        filename = f"{stem}.md"
    else:
        safe_session = sanitize_path_component(
            "".join(c if c.isalnum() or c in "-_" else "_" for c in session_id) or "session",
            field="session_id",
        )
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        filename = f"{safe_session}_{stamp}.md"
    return directory / filename


def format_export_markdown(
    body: str,
    *,
    node_name: str,
    node_slug: str,
    session_id: str,
    category: str = "",
) -> str:
    lines = [
        "---",
        f"node: {node_name}",
        f"node_slug: {node_slug}",
        f"session_id: {session_id}",
    ]
    if category:
        lines.append(f"category: {category}")
    lines.extend(["---", "", body.strip(), ""])
    return "\n".join(lines)


def export_prompt_to_file(
    *,
    response_text: str,
    node_name: str,
    node_slug: str,
    session_id: str,
    export_filename: str = "",
    category: str = "",
    output_root: Path | None = None,
) -> str:
    """写入 Markdown 文件，返回绝对路径字符串。"""
    if not (response_text or "").strip():
        raise ValueError("export_to_file requires non-empty response_text")

    root = output_root or resolve_comfy_output_root()
    path = build_export_path(root, node_slug, session_id, export_filename)
    content = format_export_markdown(
        response_text,
        node_name=node_name,
        node_slug=node_slug,
        session_id=session_id,
        category=category,
    )
    path.write_text(content, encoding="utf-8")
    return str(path.resolve())


def build_text_export_path(
    output_root: Path,
    output_subdir: str,
    filename: str,
    extension: str,
    *,
    append_timestamp: bool = True,
) -> Path:
    subdir = sanitize_relative_subdir(
        output_subdir or "ryan_acp_exports/manual",
        field="output_subdir",
    )
    directory = resolve_under_root(output_root, *subdir.split("/"))
    directory.mkdir(parents=True, exist_ok=True)
    ext = extension.lstrip(".") or "txt"
    ext = sanitize_path_component(ext, field="extension")
    raw_stem = (filename or "export").strip()
    stem = Path(raw_stem).name
    if stem.endswith(f".{ext}"):
        stem = stem[: -(len(ext) + 1)]
    stem = sanitize_path_component(stem or "export", field="filename")
    if append_timestamp:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        stem = f"{stem}_{stamp}" if stem else stamp
    return directory / f"{stem}.{ext}"


def write_text_export(
    *,
    text: str,
    output_subdir: str = "ryan_acp_exports/manual",
    filename: str = "",
    extension: str = "txt",
    append_timestamp: bool = True,
    overwrite: bool = False,
    output_root: Path | None = None,
) -> str:
    if text is None:
        raise ValueError("text is required")
    root = output_root or resolve_comfy_output_root()
    path = build_text_export_path(
        root,
        output_subdir,
        filename or "export",
        extension,
        append_timestamp=append_timestamp,
    )
    if path.exists() and not overwrite:
        raise FileExistsError(f"Refusing to overwrite: {path}")
    if extension.lower() == "json":
        import json

        try:
            parsed = json.loads(text)
            body = json.dumps(parsed, ensure_ascii=False, indent=2)
        except json.JSONDecodeError:
            body = json.dumps({"content": text}, ensure_ascii=False, indent=2)
        path.write_text(body + "\n", encoding="utf-8")
    else:
        path.write_text(text, encoding="utf-8")
    return str(path.resolve())
