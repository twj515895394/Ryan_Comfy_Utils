"""读取 Workflow Agent 的 Skill 合同，统一服务层的解析边界。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable, Mapping

from .identity import validate_id


class SkillContractError(ValueError):
    """Skill 合同缺失或不合法。"""


def _validate_output_rules(contract: Mapping[str, Any]) -> None:
    """校验阶段 Prompt kind/purpose 映射，避免 Agent 产物串阶段。"""
    kinds = contract.get("artifact_output_kinds")
    purposes = contract.get("artifact_output_purposes")
    if kinds is None and purposes is None:
        return
    if not isinstance(kinds, list) or not all(isinstance(item, str) and item.strip() for item in kinds):
        raise SkillContractError("Skill artifact_output_kinds must be an array of strings")
    if len(kinds) != len(set(kinds)):
        raise SkillContractError("Skill artifact_output_kinds must be unique")
    try:
        [validate_id(item, field="artifact_output_kinds") for item in kinds]
    except (TypeError, ValueError) as exc:
        raise SkillContractError(str(exc)) from exc
    if not isinstance(purposes, Mapping):
        raise SkillContractError("Skill artifact_output_purposes must be an object")
    unknown = set(purposes) - set(kinds)
    if unknown:
        raise SkillContractError(
            "Skill artifact_output_purposes has unknown kinds: " + ", ".join(sorted(unknown))
        )
    for kind, values in purposes.items():
        if not isinstance(values, list) or not all(isinstance(item, str) and item.strip() for item in values):
            raise SkillContractError(f"Skill purposes for {kind!r} must be an array of strings")
        if len(values) != len(set(values)):
            raise SkillContractError(f"Skill purposes for {kind!r} must be unique")


def load_skill_contract(
    skill_id: str,
    payload: Mapping[str, Any],
    resolver: Callable[[str], Path] | None = None,
) -> tuple[Path, dict[str, Any]]:
    explicit = payload.get("skill_directory")
    if explicit:
        directory = Path(str(explicit))
    elif resolver:
        directory = Path(resolver(skill_id))
    else:
        from ..acp.skill_loader import resolve_skill_directory, resolve_skill_root

        directory = resolve_skill_directory(resolve_skill_root(str(payload.get("skill_root", ""))), skill_id)
    directory = directory.expanduser().absolute()
    path = directory / "agent-contract.json"
    if not path.exists() or not path.is_file():
        raise SkillContractError(f"Skill {skill_id!r} has no agent-contract.json")
    try:
        contract = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SkillContractError("Skill agent contract is invalid") from exc
    if not isinstance(contract, dict):
        raise SkillContractError("Skill agent contract is invalid")
    kind = contract.get("produces_context_kind")
    if not isinstance(kind, str) or not kind.strip():
        raise SkillContractError("Skill agent contract has no produces_context_kind")
    _validate_output_rules(contract)
    return directory, contract


__all__ = ["SkillContractError", "load_skill_contract"]
