"""解析 ACP 节点最终绑定的 Skill（Fixed / Selectable）。"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .skill_loader import resolve_skill_directory, resolve_skill_root


@dataclass(frozen=True)
class SkillBinding:
    skill_id: str
    skill_root: Path
    skill_dir: Path
    mode: str  # fixed | selectable
    source: str  # manifest | user_input


def resolve_skill_binding(
    manifest: dict,
    skill_root_text: str,
    user_skill_id: str = "",
    allow_user_skill: bool = False,
) -> SkillBinding:
    manifest_skill = (manifest.get("skill_id") or "").strip()
    user_skill = (user_skill_id or "").strip()

    if allow_user_skill and user_skill:
        skill_id = user_skill
        source = "user_input"
        mode = "selectable"
    else:
        if not manifest_skill and allow_user_skill:
            raise ValueError("Selectable mode requires manifest.skill_id or user skill_id")
        if not manifest_skill:
            raise ValueError("Fixed manifest must define skill_id")
        skill_id = manifest_skill
        source = "manifest"
        mode = "fixed" if not allow_user_skill else "selectable"

    root = resolve_skill_root(skill_root_text)
    if skill_id == "none":
        skill_dir = root
    else:
        skill_dir = resolve_skill_directory(root, skill_id)
        
    return SkillBinding(
        skill_id=skill_id,
        skill_root=root,
        skill_dir=skill_dir,
        mode=mode,
        source=source,
    )