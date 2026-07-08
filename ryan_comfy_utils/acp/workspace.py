from pathlib import Path


def prepare_workspace(workspace_root: Path, session_id: str) -> Path:
    session_dir = workspace_root / "sessions" / session_id
    for name in ("input", "output", "logs"):
        (session_dir / name).mkdir(parents=True, exist_ok=True)
    return session_dir
