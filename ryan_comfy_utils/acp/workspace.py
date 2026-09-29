from uuid import uuid4

from pathlib import Path

from .path_safety import sanitize_path_component


def create_run_session_id(session_id: str) -> str:
    """Create a collision-resistant workspace id for one ACP execution."""
    base = sanitize_path_component(session_id, field="session_id")
    # Keep the generated component below the path-safety limit while retaining
    # the caller's logical name for diagnostics and manual cleanup.
    return f"{base[:72]}__run_{uuid4().hex}"


def prepare_workspace(workspace_root: Path, session_id: str) -> Path:
    safe_id = sanitize_path_component(session_id, field="session_id")
    session_dir = workspace_root / "sessions" / safe_id
    for name in ("input", "output", "logs"):
        (session_dir / name).mkdir(parents=True, exist_ok=True)
    return session_dir
