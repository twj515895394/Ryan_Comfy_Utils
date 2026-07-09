from pathlib import Path


def session_input_images_dir(session_dir: Path) -> Path:
    """槽位 PNG 直接写入 session 内 input/images，避免额外 staging 树。"""
    return session_dir / "input" / "images"
