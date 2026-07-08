import shutil
from pathlib import Path


def _copy_assets(session_dir: Path, category: str, source_paths: list[str]) -> list[str]:
    if not source_paths:
        return []

    target_dir = session_dir / "input" / category
    target_dir.mkdir(parents=True, exist_ok=True)

    saved_paths = []
    for source_text in source_paths:
        source_path = Path(source_text).expanduser()
        if not source_path.exists():
            raise FileNotFoundError(f"Asset not found: {source_path}")
        target_path = target_dir / source_path.name
        shutil.copy2(source_path, target_path)
        saved_paths.append(str(Path("input") / category / source_path.name))
    return saved_paths


def materialize_input_assets(
    session_dir: Path,
    image_inputs: list[str] | None = None,
    file_inputs: list[str] | None = None,
) -> dict:
    return {
        "images": _copy_assets(session_dir, "images", image_inputs or []),
        "files": _copy_assets(session_dir, "files", file_inputs or []),
    }
