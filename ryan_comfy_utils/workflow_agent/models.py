"""RYAN_CONTEXT V1 的标准库数据模型。

Context 只保存可追溯的 Canonical Commit 与资源引用；聊天记录、Tensor 和二进制
必须留在 Agent Session / Asset 仓库中，不能通过这个模块进入 DAG。
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Mapping

from .identity import validate_agent_uid, validate_id, validate_workflow_id

RYAN_CONTEXT = "RYAN_CONTEXT"


class ContextValidationError(ValueError):
    """RYAN_CONTEXT 字段或 JSON 结构不符合 V1 合同。"""


def _json_safe(value: Any, *, path: str = "payload") -> Any:
    """复制并校验 JSON 值，明确拒绝隐式序列化的运行时对象。"""
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise TypeError(f"{path} must not contain NaN or infinity")
        return value
    if isinstance(value, Mapping):
        result: dict[str, Any] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise TypeError(f"{path} object keys must be strings")
            result[key] = _json_safe(item, path=f"{path}.{key}")
        return result
    if isinstance(value, (list, tuple)):
        return [_json_safe(item, path=f"{path}[{index}]") for index, item in enumerate(value)]
    raise TypeError(f"{path} contains a non-JSON value: {type(value).__name__}")


def _text(value: Any, field_name: str, *, required: bool = False) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be a string")
    if required:
        return validate_id(value, field=field_name)
    return value


def _mapping(value: Any, field_name: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise TypeError(f"{field_name} must be an object")
    return _json_safe(value, path=field_name)


def _string_list(value: Any, field_name: str) -> list[str]:
    if not isinstance(value, (list, tuple)):
        raise TypeError(f"{field_name} must be an array")
    result = []
    for index, item in enumerate(value):
        result.append(validate_id(item, field=f"{field_name}[{index}]") )
    return result


@dataclass(slots=True)
class RyanAssetRef:
    asset_id: str
    workflow_id: str
    type: str = "other"
    mime_type: str = ""
    display_name: str = ""
    source: str = ""
    uri: str = ""
    size_bytes: int | None = None
    created_by_agent_uid: str = ""
    created_at: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.asset_id = validate_id(self.asset_id, field="asset_id")
        self.workflow_id = validate_workflow_id(self.workflow_id)
        self.type = _text(self.type, "type")
        self.mime_type = _text(self.mime_type, "mime_type")
        self.display_name = _text(self.display_name, "display_name")
        self.source = _text(self.source, "source")
        self.uri = _text(self.uri, "uri")
        if self.size_bytes is not None:
            if isinstance(self.size_bytes, bool) or not isinstance(self.size_bytes, int):
                raise TypeError("size_bytes must be an integer or null")
            if self.size_bytes < 0:
                raise ValueError("size_bytes must not be negative")
        if self.created_by_agent_uid:
            self.created_by_agent_uid = validate_agent_uid(self.created_by_agent_uid)
        self.created_at = _text(self.created_at, "created_at")
        self.metadata = _mapping(self.metadata, "metadata")

    def to_dict(self) -> dict[str, Any]:
        return _json_safe(
            {
                "asset_id": self.asset_id,
                "workflow_id": self.workflow_id,
                "type": self.type,
                "mime_type": self.mime_type,
                "display_name": self.display_name,
                "source": self.source,
                "uri": self.uri,
                "size_bytes": self.size_bytes,
                "created_by_agent_uid": self.created_by_agent_uid,
                "created_at": self.created_at,
                "metadata": self.metadata,
            }
        )

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "RyanAssetRef":
        if not isinstance(payload, Mapping):
            raise TypeError("asset payload must be an object")
        return cls(
            asset_id=payload.get("asset_id", ""),
            workflow_id=payload.get("workflow_id", ""),
            type=payload.get("type", "other"),
            mime_type=payload.get("mime_type", ""),
            display_name=payload.get("display_name", ""),
            source=payload.get("source", ""),
            uri=payload.get("uri", ""),
            size_bytes=payload.get("size_bytes"),
            created_by_agent_uid=payload.get("created_by_agent_uid", ""),
            created_at=payload.get("created_at", ""),
            metadata=payload.get("metadata", {}),
        )


@dataclass(slots=True)
class RyanContextEntry:
    entry_id: str
    workflow_id: str
    source_agent_uid: str
    kind: str
    source_agent_name: str = ""
    skill_id: str = ""
    revision: int = 0
    title: str = ""
    summary: str = ""
    content_format: str = "markdown"
    content: str = ""
    asset_refs: list[str] = field(default_factory=list)
    upstream_entry_ids: list[str] = field(default_factory=list)
    created_at: str = ""
    status: str = "active"
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.entry_id = validate_id(self.entry_id, field="entry_id")
        self.workflow_id = validate_workflow_id(self.workflow_id)
        self.source_agent_uid = validate_agent_uid(self.source_agent_uid)
        self.kind = validate_id(self.kind, field="kind")
        for name in ("source_agent_name", "skill_id", "title", "summary", "content_format", "content", "created_at", "status"):
            setattr(self, name, _text(getattr(self, name), name))
        if isinstance(self.revision, bool) or not isinstance(self.revision, int):
            raise TypeError("revision must be an integer")
        if self.revision < 0:
            raise ValueError("revision must not be negative")
        self.asset_refs = _string_list(self.asset_refs, "asset_refs")
        self.upstream_entry_ids = _string_list(self.upstream_entry_ids, "upstream_entry_ids")
        self.metadata = _mapping(self.metadata, "metadata")
        if self.status not in {"active", "superseded", "withdrawn"}:
            raise ValueError("status must be active, superseded, or withdrawn")

    def to_dict(self) -> dict[str, Any]:
        return _json_safe(
            {
                "entry_id": self.entry_id,
                "workflow_id": self.workflow_id,
                "source_agent_uid": self.source_agent_uid,
                "source_agent_name": self.source_agent_name,
                "skill_id": self.skill_id,
                "kind": self.kind,
                "revision": self.revision,
                "title": self.title,
                "summary": self.summary,
                "content_format": self.content_format,
                "content": self.content,
                "asset_refs": list(self.asset_refs),
                "upstream_entry_ids": list(self.upstream_entry_ids),
                "created_at": self.created_at,
                "status": self.status,
                "metadata": self.metadata,
            }
        )

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "RyanContextEntry":
        if not isinstance(payload, Mapping):
            raise TypeError("entry payload must be an object")
        return cls(
            entry_id=payload.get("entry_id", ""),
            workflow_id=payload.get("workflow_id", ""),
            source_agent_uid=payload.get("source_agent_uid", ""),
            source_agent_name=payload.get("source_agent_name", ""),
            skill_id=payload.get("skill_id", ""),
            kind=payload.get("kind", ""),
            revision=payload.get("revision", 0),
            title=payload.get("title", ""),
            summary=payload.get("summary", ""),
            content_format=payload.get("content_format", "markdown"),
            content=payload.get("content", ""),
            asset_refs=payload.get("asset_refs", []),
            upstream_entry_ids=payload.get("upstream_entry_ids", []),
            created_at=payload.get("created_at", ""),
            status=payload.get("status", "active"),
            metadata=payload.get("metadata", {}),
        )


@dataclass(slots=True)
class RyanContextLineage:
    lineage_id: str
    workflow_id: str
    entry_id: str = ""
    commit_id: str = ""
    source_agent_uid: str = ""
    revision: int = 0
    upstream_entry_ids: list[str] = field(default_factory=list)
    created_at: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.lineage_id = validate_id(self.lineage_id, field="lineage_id")
        self.workflow_id = validate_workflow_id(self.workflow_id)
        if self.entry_id:
            self.entry_id = validate_id(self.entry_id, field="entry_id")
        if self.commit_id:
            self.commit_id = validate_id(self.commit_id, field="commit_id")
        if self.source_agent_uid:
            self.source_agent_uid = validate_agent_uid(self.source_agent_uid)
        if isinstance(self.revision, bool) or not isinstance(self.revision, int):
            raise TypeError("revision must be an integer")
        if self.revision < 0:
            raise ValueError("revision must not be negative")
        self.upstream_entry_ids = _string_list(self.upstream_entry_ids, "upstream_entry_ids")
        self.created_at = _text(self.created_at, "created_at")
        self.metadata = _mapping(self.metadata, "metadata")

    def to_dict(self) -> dict[str, Any]:
        return _json_safe(
            {
                "lineage_id": self.lineage_id,
                "workflow_id": self.workflow_id,
                "entry_id": self.entry_id,
                "commit_id": self.commit_id,
                "source_agent_uid": self.source_agent_uid,
                "revision": self.revision,
                "upstream_entry_ids": list(self.upstream_entry_ids),
                "created_at": self.created_at,
                "metadata": self.metadata,
            }
        )

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "RyanContextLineage":
        if not isinstance(payload, Mapping):
            raise TypeError("lineage payload must be an object")
        return cls(
            lineage_id=payload.get("lineage_id", payload.get("commit_id", "")),
            workflow_id=payload.get("workflow_id", ""),
            entry_id=payload.get("entry_id", ""),
            commit_id=payload.get("commit_id", ""),
            source_agent_uid=payload.get("source_agent_uid", ""),
            revision=payload.get("revision", 0),
            upstream_entry_ids=payload.get("upstream_entry_ids", []),
            created_at=payload.get("created_at", ""),
            metadata=payload.get("metadata", {}),
        )


# 两个可读别名，兼容“lineage reference”在调用侧的不同命名。
RyanContextLineageRef = RyanContextLineage
RyanLineageRef = RyanContextLineage


@dataclass(slots=True)
class RyanContext:
    workflow_id: str
    entries: list[RyanContextEntry] = field(default_factory=list)
    assets: list[RyanAssetRef] = field(default_factory=list)
    lineage: list[RyanContextLineage] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    schema_version: int = 1

    def __post_init__(self) -> None:
        if isinstance(self.schema_version, bool) or self.schema_version != 1:
            raise ValueError("schema_version must be 1")
        self.workflow_id = validate_workflow_id(self.workflow_id)
        if not isinstance(self.entries, list):
            raise TypeError("entries must be an array")
        if not isinstance(self.assets, list):
            raise TypeError("assets must be an array")
        if not isinstance(self.lineage, list):
            raise TypeError("lineage must be an array")
        normalized_entries = []
        for value in self.entries:
            normalized_entries.append(value if isinstance(value, RyanContextEntry) else RyanContextEntry.from_dict(value))
        normalized_assets = []
        for value in self.assets:
            normalized_assets.append(value if isinstance(value, RyanAssetRef) else RyanAssetRef.from_dict(value))
        normalized_lineage = []
        for value in self.lineage:
            normalized_lineage.append(value if isinstance(value, RyanContextLineage) else RyanContextLineage.from_dict(value))
        for entry in normalized_entries:
            if entry.workflow_id != self.workflow_id:
                raise ContextValidationError("entry workflow_id does not match context workflow_id")
        for asset in normalized_assets:
            if asset.workflow_id != self.workflow_id:
                raise ContextValidationError("asset workflow_id does not match context workflow_id")
        for item in normalized_lineage:
            if item.workflow_id != self.workflow_id:
                raise ContextValidationError("lineage workflow_id does not match context workflow_id")
        self.entries = normalized_entries
        self.assets = normalized_assets
        self.lineage = normalized_lineage
        self.metadata = _mapping(self.metadata, "metadata")

    def to_dict(self) -> dict[str, Any]:
        return _json_safe(
            {
                "schema_version": 1,
                "workflow_id": self.workflow_id,
                "entries": [entry.to_dict() for entry in self.entries],
                "assets": [asset.to_dict() for asset in self.assets],
                "lineage": [item.to_dict() for item in self.lineage],
                "metadata": self.metadata,
            }
        )

    def to_json(self, **kwargs: Any) -> str:
        import json

        options = {"ensure_ascii": False, "sort_keys": True, "allow_nan": False}
        options.update(kwargs)
        return json.dumps(self.to_dict(), **options)

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "RyanContext":
        if not isinstance(payload, Mapping):
            raise TypeError("context payload must be an object")
        if "chat_history" in payload or "messages" in payload:
            raise ContextValidationError("chat history is not part of RYAN_CONTEXT")
        return cls(
            schema_version=payload.get("schema_version", 1),
            workflow_id=payload.get("workflow_id", ""),
            entries=[RyanContextEntry.from_dict(item) for item in payload.get("entries", [])],
            assets=[RyanAssetRef.from_dict(item) for item in payload.get("assets", [])],
            lineage=[RyanContextLineage.from_dict(item) for item in payload.get("lineage", [])],
            metadata=payload.get("metadata", {}),
        )

    def clone(self) -> "RyanContext":
        return RyanContext.from_dict(self.to_dict())


__all__ = [
    "RYAN_CONTEXT",
    "ContextValidationError",
    "RyanAssetRef",
    "RyanContext",
    "RyanContextEntry",
    "RyanContextLineage",
    "RyanContextLineageRef",
    "RyanLineageRef",
]
