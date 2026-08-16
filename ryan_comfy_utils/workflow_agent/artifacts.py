"""Workflow Agent Commit 的结构化产物合同与安全解析。"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field, replace
from typing import Any, Iterable, Mapping

from .identity import validate_id
from .models import RyanContextEntry, _json_safe


_ARTIFACT_BLOCK = re.compile(r"```ryan-artifact(?:[ \t]+)?\r?\n(.*?)\r?\n?```", re.DOTALL)


class ArtifactValidationError(ValueError):
    """结构化产物不符合 V1/V2 合同。"""


def _required_string_list(value: Any, field_name: str) -> list[str]:
    if not isinstance(value, list) or not all(isinstance(item, str) and item.strip() for item in value):
        raise ArtifactValidationError(f"{field_name} must be an array of non-empty strings")
    return value


def _required_content_v2(value: Mapping[str, Any]) -> dict[str, Any]:
    required = ("summary", "handoff", "locks")
    missing = [name for name in required if name not in value]
    if missing:
        raise ArtifactValidationError(
            f"content must include {', '.join(missing)} for schema_version 2"
        )
    for name in ("summary", "handoff"):
        if not isinstance(value[name], str) or not value[name].strip():
            raise ArtifactValidationError(f"content.{name} must be a non-empty string")
    return {
        **dict(value),
        "summary": value["summary"],
        "handoff": value["handoff"],
        "locks": _required_string_list(value["locks"], "content.locks"),
    }

def _required_text(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ArtifactValidationError(f"{field_name} must be a non-empty string")
    return value


def _optional_text(value: Any, field_name: str) -> str:
    if not isinstance(value, str):
        raise ArtifactValidationError(f"{field_name} must be a string")
    return value


def _priority(value: Any) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ArtifactValidationError("priority must be an integer")
    if not 0 <= value <= 100:
        raise ArtifactValidationError("priority must be between 0 and 100")
    return value


def _copy_legacy_alias(
    payload: Mapping[str, Any],
    normalized: dict[str, Any],
    target: str,
    aliases: tuple[str, ...],
) -> None:
    """将旧字段复制到规范字段；冲突值必须显式失败。"""
    if target in normalized:
        return
    values = [payload[name] for name in aliases if name in payload]
    if not values:
        return
    non_empty = [value for value in values if isinstance(value, str) and value.strip()]
    if len({value for value in non_empty}) > 1:
        raise ArtifactValidationError(f"conflicting legacy values for {target}")
    normalized[target] = values[0]


def _normalize_legacy_output(payload: Any) -> Any:
    if not isinstance(payload, Mapping):
        return payload
    if "prompt_en" in payload or "text_en" in payload:
        raise ArtifactValidationError("bilingual prompt fields are not supported; use text")
    normalized = dict(payload)
    _copy_legacy_alias(payload, normalized, "output_id", ("id",))
    _copy_legacy_alias(payload, normalized, "text", ("prompt", "constraint"))
    if "label" not in normalized:
        normalized["label"] = payload.get("role") or payload.get("id", "")
    reference_roles = normalized.get("reference_roles")
    if isinstance(reference_roles, Mapping):
        sanitized_roles = dict(reference_roles)
        removed_scalar_roles = False
        for role, values in reference_roles.items():
            if isinstance(values, str):
                # 旧模型常把无资产时的文件名写成字符串；无法安全绑定时仅丢弃该角色，
                # 保留同一输出中已经符合合同的 AssetRef 数组。
                sanitized_roles.pop(role, None)
                removed_scalar_roles = True
        if removed_scalar_roles:
            normalized["reference_roles"] = sanitized_roles
    return normalized


def _normalize_legacy_shot(payload: Any) -> Any:
    if not isinstance(payload, Mapping):
        return payload
    normalized = dict(payload)
    _copy_legacy_alias(payload, normalized, "shot_id", ("id",))
    _copy_legacy_alias(payload, normalized, "prompt", ("text", "constraint"))
    if "label" not in normalized:
        normalized["label"] = payload.get("role") or payload.get("id", "")
    return normalized


def normalize_artifact_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    """把旧版 Bundle 字段规范化为 V1；无法安全转换的值交给严格校验。"""
    if not isinstance(payload, Mapping):
        raise ArtifactValidationError("artifact bundle must be an object")
    normalized = dict(payload)
    content = payload.get("content")
    if content is None:
        content = {}
    elif isinstance(content, Mapping):
        content = dict(content)
    for key, value in payload.items():
        if key not in {"artifact_type", "schema_version", "outputs", "shots", "content"}:
            if isinstance(content, dict):
                content.setdefault(key, value)
    normalized["content"] = content
    if "schema_version" not in normalized:
        normalized["schema_version"] = 1
    outputs = payload.get("outputs", [])
    shots = payload.get("shots", [])
    normalized["outputs"] = (
        [_normalize_legacy_output(item) for item in outputs] if isinstance(outputs, list) else outputs
    )
    normalized["shots"] = (
        [_normalize_legacy_shot(item) for item in shots] if isinstance(shots, list) else shots
    )
    return normalized


def normalize_entry_artifact(entry: RyanContextEntry) -> RyanContextEntry:
    """将 Entry 正文中的旧 Bundle 提升为 Context 可传输的规范 metadata。"""
    if not isinstance(entry, RyanContextEntry):
        raise TypeError("entry must be RyanContextEntry")
    parsed = parse_artifact_markdown(entry.content)
    if parsed.status != "valid" or parsed.bundle is None:
        return entry
    metadata = dict(entry.metadata)
    metadata["artifact_bundle"] = parsed.bundle.to_dict()
    metadata["artifact_status"] = "valid"
    metadata.pop("artifact_error", None)
    return replace(entry, content=parsed.cleaned_text, metadata=metadata)
@dataclass(slots=True)
class RyanArtifactOutput:
    output_id: str
    kind: str
    label: str
    text: str
    priority: int = 50
    purpose: str = ""
    target_ids: list[str] = field(default_factory=list)
    reference_roles: dict[str, list[str]] = field(default_factory=dict)
    negative_constraints: list[str] = field(default_factory=list)
    aspect_ratio: str = ""

    def __post_init__(self) -> None:
        self.output_id = validate_id(self.output_id, field="output_id")
        self.kind = validate_id(self.kind, field="kind")
        self.label = _required_text(self.label, "label")
        self.text = _required_text(self.text, "text")
        self.priority = _priority(self.priority)
        self.purpose = _optional_text(self.purpose, "purpose")
        if not isinstance(self.target_ids, list):
            raise ArtifactValidationError("target_ids must be an array")
        self.target_ids = [validate_id(value, field="target_ids") for value in self.target_ids]
        if len(self.target_ids) != len(set(self.target_ids)):
            raise ArtifactValidationError("target_ids values must be unique")
        if not isinstance(self.reference_roles, Mapping):
            raise ArtifactValidationError("reference_roles must be an object")
        for role, values in self.reference_roles.items():
            if not isinstance(role, str) or not isinstance(values, list):
                raise ArtifactValidationError("reference_roles must contain arrays")
        self.reference_roles = {
            role: [validate_id(value, field=f"reference_roles.{role}") for value in values]
            for role, values in self.reference_roles.items()
        }
        if not isinstance(self.negative_constraints, list) or not all(
            isinstance(value, str) for value in self.negative_constraints
        ):
            raise ArtifactValidationError("negative_constraints must be an array of strings")
        self.aspect_ratio = _optional_text(self.aspect_ratio, "aspect_ratio")

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "output_id": self.output_id,
            "kind": self.kind,
            "label": self.label,
            "text": self.text,
            "priority": self.priority,
        }
        # 可选元数据只在确实提供时写出，避免把空字段伪装成 Prompt 语义。
        if self.purpose:
            result["purpose"] = self.purpose
        if self.target_ids:
            result["target_ids"] = list(self.target_ids)
        if self.reference_roles:
            result["reference_roles"] = {
                key: list(value) for key, value in self.reference_roles.items()
            }
        if self.negative_constraints:
            result["negative_constraints"] = list(self.negative_constraints)
        if self.aspect_ratio:
            result["aspect_ratio"] = self.aspect_ratio
        return result

    @classmethod
    def from_dict(
        cls, payload: Mapping[str, Any], *, strict_v2: bool = False
    ) -> "RyanArtifactOutput":
        if not isinstance(payload, Mapping):
            raise ArtifactValidationError("output must be an object")
        normalized = _normalize_legacy_output(payload)
        if strict_v2 and (
            not isinstance(normalized.get("purpose"), str)
            or not normalized.get("purpose", "").strip()
        ):
            raise ArtifactValidationError("purpose must be a non-empty string for schema_version 2")
        if strict_v2 and (
            not isinstance(normalized.get("target_ids"), list) or not normalized["target_ids"]
        ):
            raise ArtifactValidationError("target_ids must be a non-empty array for schema_version 2")
        return cls(
            output_id=normalized.get("output_id", ""),
            kind=normalized.get("kind", ""),
            label=normalized.get("label", ""),
            text=normalized.get("text", ""),
            priority=normalized.get("priority", 50),
            purpose=normalized.get("purpose", ""),
            target_ids=normalized.get("target_ids", []),
            reference_roles=normalized.get("reference_roles", {}),
            negative_constraints=normalized.get("negative_constraints", []),
            aspect_ratio=normalized.get("aspect_ratio", ""),
        )


@dataclass(slots=True)
class RyanArtifactShot:
    shot_id: str
    prompt: str
    kind: str = "shot_prompt"
    label: str = ""
    priority: int = 50

    def __post_init__(self) -> None:
        self.shot_id = validate_id(self.shot_id, field="shot_id")
        self.prompt = _required_text(self.prompt, "prompt")
        self.kind = validate_id(self.kind, field="kind")
        self.label = _optional_text(self.label, "label")
        self.priority = _priority(self.priority)

    def to_dict(self) -> dict[str, Any]:
        return {
            "shot_id": self.shot_id,
            "prompt": self.prompt,
            "kind": self.kind,
            "label": self.label,
            "priority": self.priority,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "RyanArtifactShot":
        if not isinstance(payload, Mapping):
            raise ArtifactValidationError("shot must be an object")
        normalized = _normalize_legacy_shot(payload)
        return cls(
            shot_id=normalized.get("shot_id", ""),
            prompt=normalized.get("prompt", ""),
            kind=normalized.get("kind", "shot_prompt"),
            label=normalized.get("label", ""),
            priority=normalized.get("priority", 50),
        )


@dataclass(slots=True)
class RyanArtifactBundle:
    artifact_type: str
    content: dict[str, Any] = field(default_factory=dict)
    outputs: list[RyanArtifactOutput] = field(default_factory=list)
    shots: list[RyanArtifactShot] = field(default_factory=list)
    schema_version: int = 1

    def __post_init__(self) -> None:
        self.artifact_type = validate_id(self.artifact_type, field="artifact_type")
        if isinstance(self.schema_version, bool) or self.schema_version not in {1, 2}:
            raise ArtifactValidationError("schema_version must be 1 or 2")
        try:
            self.content = _json_safe(self.content, path="content")
        except (TypeError, ValueError) as exc:
            raise ArtifactValidationError(str(exc)) from exc
        if not isinstance(self.content, dict):
            raise ArtifactValidationError("content must be an object")
        if self.schema_version == 2:
            self.content = _required_content_v2(self.content)
        self.outputs = [
            item
            if isinstance(item, RyanArtifactOutput)
            else RyanArtifactOutput.from_dict(item, strict_v2=self.schema_version == 2)
            for item in self.outputs
        ]
        self.shots = [
            item if isinstance(item, RyanArtifactShot) else RyanArtifactShot.from_dict(item)
            for item in self.shots
        ]
        output_ids = [item.output_id for item in self.outputs]
        if len(output_ids) != len(set(output_ids)):
            raise ArtifactValidationError("output_id values must be unique")
        shot_ids = [item.shot_id for item in self.shots]
        if len(shot_ids) != len(set(shot_ids)):
            raise ArtifactValidationError("shot_id values must be unique")

    def to_dict(self) -> dict[str, Any]:
        return {
            "artifact_type": self.artifact_type,
            "schema_version": self.schema_version,
            "content": _json_safe(self.content, path="content"),
            "outputs": [item.to_dict() for item in self.outputs],
            "shots": [item.to_dict() for item in self.shots],
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "RyanArtifactBundle":
        normalized = normalize_artifact_payload(payload)
        outputs = normalized.get("outputs", [])
        shots = normalized.get("shots", [])
        if not isinstance(outputs, list) or not isinstance(shots, list):
            raise ArtifactValidationError("outputs and shots must be arrays")
        return cls(
            artifact_type=normalized.get("artifact_type", ""),
            schema_version=normalized.get("schema_version", 1),
            content=normalized.get("content", {}),
            outputs=outputs,
            shots=shots,
        )


@dataclass(slots=True)
class ArtifactParseResult:
    cleaned_text: str
    status: str
    bundle: RyanArtifactBundle | None = None
    error: str = ""


def parse_artifact_markdown(
    text: str,
    *,
    expected_artifact_type: str = "",
    allowed_output_kinds: Iterable[str] | None = None,
    allowed_output_purposes: Mapping[str, Iterable[str]] | None = None,
) -> ArtifactParseResult:
    """解析唯一 artifact block，并可按阶段合同校验 Prompt 类型与用途。"""
    if not isinstance(text, str):
        raise TypeError("artifact Markdown must be a string")
    matches = list(_ARTIFACT_BLOCK.finditer(text))
    if not matches:
        return ArtifactParseResult(cleaned_text=text, status="absent")
    if len(matches) != 1:
        return ArtifactParseResult(text, "invalid", error="exactly one artifact block is allowed")
    match = matches[0]
    try:
        payload = json.loads(match.group(1))
        bundle = RyanArtifactBundle.from_dict(payload)
        if expected_artifact_type and bundle.artifact_type != expected_artifact_type:
            raise ArtifactValidationError(
                f"artifact_type must be {expected_artifact_type!r}, got {bundle.artifact_type!r}"
            )
        if allowed_output_kinds is not None and bundle.schema_version == 2:
            allowed = {str(value) for value in allowed_output_kinds}
            unexpected = sorted({output.kind for output in bundle.outputs if output.kind not in allowed})
            if unexpected:
                raise ArtifactValidationError(
                    "output kinds not allowed for this Skill: " + ", ".join(unexpected)
                )
        if allowed_output_purposes is not None and bundle.schema_version == 2:
            for output in bundle.outputs:
                if output.kind not in allowed_output_purposes:
                    continue
                allowed = {
                    str(value)
                    for value in allowed_output_purposes[output.kind]
                }
                if output.purpose not in allowed:
                    raise ArtifactValidationError(
                        f"purpose {output.purpose!r} not allowed for {output.kind}: "
                        + ", ".join(sorted(allowed))
                    )
    except (ArtifactValidationError, TypeError, ValueError, json.JSONDecodeError) as exc:
        return ArtifactParseResult(text, "invalid", error=str(exc))
    cleaned = (text[: match.start()] + text[match.end() :]).strip()
    return ArtifactParseResult(cleaned_text=cleaned, status="valid", bundle=bundle)


def artifact_bundle_from_entry(entry: RyanContextEntry) -> RyanArtifactBundle | None:
    if not isinstance(entry, RyanContextEntry):
        raise TypeError("entry must be RyanContextEntry")
    value = entry.metadata.get("artifact_bundle")
    if isinstance(value, Mapping):
        try:
            return RyanArtifactBundle.from_dict(value)
        except (ArtifactValidationError, TypeError, ValueError):
            pass
    parsed = parse_artifact_markdown(entry.content)
    return parsed.bundle if parsed.status == "valid" else None


def artifact_outputs(entry: RyanContextEntry) -> list[RyanArtifactOutput]:
    bundle = artifact_bundle_from_entry(entry)
    return list(bundle.outputs) if bundle else []


def artifact_shots(entry: RyanContextEntry) -> list[RyanArtifactShot]:
    bundle = artifact_bundle_from_entry(entry)
    return list(bundle.shots) if bundle else []


def artifact_summary(entry: RyanContextEntry) -> str:
    bundle = artifact_bundle_from_entry(entry)
    if bundle:
        parts: list[str] = []
        summary = bundle.content.get("summary")
        handoff = bundle.content.get("handoff")
        locks = bundle.content.get("locks")
        if isinstance(summary, str) and summary.strip():
            parts.append(f"摘要：{summary.strip()}")
        if isinstance(handoff, str) and handoff.strip():
            parts.append(f"下游交接：{handoff.strip()}")
        if isinstance(locks, list):
            lock_text = "；".join(str(item).strip() for item in locks if str(item).strip())
            if lock_text:
                parts.append(f"已确认锁：{lock_text}")
        if parts:
            return "\n".join(parts)
    return entry.summary or entry.content[:12000]


__all__ = [
    "ArtifactParseResult",
    "ArtifactValidationError",
    "RyanArtifactBundle",
    "RyanArtifactOutput",
    "RyanArtifactShot",
    "artifact_bundle_from_entry",
    "artifact_outputs",
    "artifact_shots",
    "artifact_summary",
    "normalize_artifact_payload",
    "normalize_entry_artifact",
    "parse_artifact_markdown",
]
