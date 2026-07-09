import shutil
from pathlib import Path


def _relative_under_session_input(session_dir: Path, source_path: Path) -> str | None:
    """若源文件已在 session_dir/input 下，返回相对 session 的 posix 路径，否则 None。"""
    try:
        rel = source_path.resolve().relative_to((session_dir / "input").resolve())
    except ValueError:
        return None
    return str(Path("input") / rel).replace("\\", "/")


def _copy_assets(session_dir: Path, category: str, source_paths: list[str]) -> list[str]:
    if not source_paths:
        return []

    target_dir = session_dir / "input" / category
    target_dir.mkdir(parents=True, exist_ok=True)

    saved_paths = []
    for index, source_text in enumerate(source_paths, start=1):
        source_path = Path(source_text).expanduser()
        if not source_path.exists():
            raise FileNotFoundError(f"Asset not found: {source_path}")

        # 槽位已直接写入 session/input 时跳过二次 copy，避免双落盘
        already = _relative_under_session_input(session_dir, source_path)
        if already is not None:
            saved_paths.append(already)
            continue

        # 序号前缀避免同名文件静默覆盖
        target_name = f"{index:02d}_{source_path.name}"
        target_path = target_dir / target_name
        shutil.copy2(source_path, target_path)
        saved_paths.append(str(Path("input") / category / target_name).replace("\\", "/"))
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
