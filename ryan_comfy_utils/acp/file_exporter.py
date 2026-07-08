"""将 ACP 节点产出的 prompt 写入 ComfyUI output 下固定子目录。"""

from datetime import datetime, timezone
from pathlib import Path


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
    directory = output_root / EXPORT_SUBDIR / node_slug
    directory.mkdir(parents=True, exist_ok=True)
    name = (export_filename or "").strip()
    if name:
        stem = name if not name.endswith(".md") else name[:-3]
        filename = f"{stem}.md"
    else:
        safe_session = "".join(c if c.isalnum() or c in "-_" else "_" for c in session_id)
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