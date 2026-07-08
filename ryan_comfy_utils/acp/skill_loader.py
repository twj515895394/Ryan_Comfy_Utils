from pathlib import Path


def resolve_skill_directory(skill_root: Path, skill_id: str) -> Path:
    path = skill_root / skill_id
    if not path.exists():
        raise FileNotFoundError(f"Skill not found: {path}")
    return path
