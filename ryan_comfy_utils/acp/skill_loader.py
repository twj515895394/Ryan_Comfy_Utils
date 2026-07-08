from pathlib import Path

# 包内默认 skill 目录，供固定 Prompt Agent 与测试使用
_DEFAULT_FIXTURES_SKILLS = Path(__file__).resolve().parent / "fixtures" / "skills"


def resolve_skill_root(skill_root_text: str) -> Path:
    """用户未配置 skill_root 时回退到包内 fixtures/skills。"""
    text = (skill_root_text or "").strip()
    if not text:
        return _DEFAULT_FIXTURES_SKILLS
    return Path(text).expanduser()


def resolve_skill_directory(skill_root: Path, skill_id: str) -> Path:
    path = skill_root / skill_id
    if not path.exists():
        raise FileNotFoundError(f"Skill not found: {path}")
    return path