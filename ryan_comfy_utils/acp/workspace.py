from pathlib import Path

from .path_safety import sanitize_path_component


def prepare_workspace(workspace_root: Path, session_id: str) -> Path:
    safe_id = sanitize_path_component(session_id, field="session_id")
    session_dir = workspace_root / "sessions" / safe_id
    for name in ("input", "output", "logs"):
        (session_dir / name).mkdir(parents=True, exist_ok=True)
    return session_dir
