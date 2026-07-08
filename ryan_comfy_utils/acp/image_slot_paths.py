from pathlib import Path


def staging_dir_for_session(workspace_root: Path, session_id: str) -> Path:
    return workspace_root / "_ryan_image_staging" / session_id