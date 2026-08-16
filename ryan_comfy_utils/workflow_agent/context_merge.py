"""RYAN_CONTEXT 的不可变合并与当前 Commit 追加。"""

from __future__ import annotations

from typing import Any, Iterable, Mapping

from .artifacts import normalize_entry_artifact
from .identity import validate_id, validate_workflow_id
from .models import RyanAssetRef, RyanContext, RyanContextEntry, RyanContextLineage

class WorkflowContextMismatch(ValueError):
    """待合并 Context 属于不同 Workflow。"""


class ContextConflict(ValueError):
    """相同稳定 ID 对应了不一致内容。"""


def _as_context(value: RyanContext | Mapping[str, Any]) -> RyanContext:
    if isinstance(value, RyanContext):
        return value
    if isinstance(value, Mapping):
        return RyanContext.from_dict(value)
    raise TypeError("context must be RyanContext or a mapping")


def _dedupe(values: Iterable[Any], *, field: str, conflict_label: str) -> list[Any]:
    result: dict[str, Any] = {}
    for value in values:
        key = getattr(value, field)
        existing = result.get(key)
        if existing is None:
            result[key] = value
            continue
        if existing.to_dict() != value.to_dict():
            raise ContextConflict(f"{conflict_label} conflict for {field}={key!r}")
    return list(result.values())


def _stable_created(value: Any) -> tuple[str, str]:
    return (
        getattr(value, "created_at", "") or "",
        getattr(value, "entry_id", getattr(value, "asset_id", getattr(value, "lineage_id", ""))),
    )


def merge_contexts(
    contexts: Iterable[RyanContext | Mapping[str, Any] | None],
    *,
    workflow_id: str | None = None,
) -> RyanContext:
    """合并 DAG 上游 Context；不会修改任何输入对象。"""
    normalized = [_as_context(value) for value in contexts if value is not None]
    resolved_workflow = validate_workflow_id(workflow_id) if workflow_id else None
    for context in normalized:
        if resolved_workflow is None:
            resolved_workflow = context.workflow_id
        elif context.workflow_id != resolved_workflow:
            raise WorkflowContextMismatch(
                f"workflow_id mismatch: expected {resolved_workflow!r}, got {context.workflow_id!r}"
            )
    if resolved_workflow is None:
        raise ValueError("workflow_id is required when merging empty contexts")

    entries = _dedupe(
        (entry for context in normalized for entry in context.entries),
        field="entry_id",
        conflict_label="entry",
    )
    assets = _dedupe(
        (asset for context in normalized for asset in context.assets),
        field="asset_id",
        conflict_label="asset",
    )
    lineage = _dedupe(
        (item for context in normalized for item in context.lineage),
        field="lineage_id",
        conflict_label="lineage",
    )
    metadata: dict[str, Any] = {}
    for context in normalized:
        for key, value in context.metadata.items():
            if key in metadata and metadata[key] != value:
                raise ContextConflict(f"metadata conflict for key={key!r}")
            metadata[key] = value
    return RyanContext(
        workflow_id=resolved_workflow,
        entries=sorted(entries, key=_stable_created),
        assets=sorted(assets, key=_stable_created),
        lineage=sorted(lineage, key=_stable_created),
        metadata=metadata,
    )


def _commit_entry(commit: Mapping[str, Any], workflow_id: str) -> RyanContextEntry:
    nested = commit.get("entry")
    payload = dict(nested) if isinstance(nested, Mapping) else dict(commit)
    for key, value in commit.items():
        payload.setdefault(key, value)
    payload["workflow_id"] = payload.get("workflow_id") or workflow_id
    if payload["workflow_id"] != workflow_id:
        raise WorkflowContextMismatch(
            f"commit workflow_id mismatch: expected {workflow_id!r}, got {payload['workflow_id']!r}"
        )
    payload["entry_id"] = payload.get("entry_id") or payload.get("commit_id", "")
    payload["source_agent_uid"] = payload.get("source_agent_uid") or payload.get("agent_uid", "")
    payload["source_agent_name"] = payload.get("source_agent_name") or payload.get("agent_name", "")
    payload["asset_refs"] = payload.get("asset_refs", [])
    payload["upstream_entry_ids"] = payload.get("upstream_entry_ids", [])
    return normalize_entry_artifact(RyanContextEntry.from_dict(payload))


def _commit_assets(commit: Mapping[str, Any], workflow_id: str) -> list[RyanAssetRef]:
    raw_assets = commit.get("assets", [])
    if not isinstance(raw_assets, (list, tuple)):
        raise TypeError("commit assets must be an array")
    result = []
    for value in raw_assets:
        if isinstance(value, RyanAssetRef):
            asset = value
        elif isinstance(value, Mapping):
            payload = dict(value)
            payload.setdefault("workflow_id", workflow_id)
            asset = RyanAssetRef.from_dict(payload)
        else:
            continue
        if asset.workflow_id != workflow_id:
            raise WorkflowContextMismatch("commit asset workflow_id does not match context")
        result.append(asset)
    return result


def _commit_lineage(commit: Mapping[str, Any], entry: RyanContextEntry, workflow_id: str) -> list[RyanContextLineage]:
    raw = commit.get("lineage", [])
    if isinstance(raw, Mapping):
        raw = [raw]
    if not isinstance(raw, (list, tuple)):
        raise TypeError("commit lineage must be an array or object")
    result = []
    for value in raw:
        if isinstance(value, RyanContextLineage):
            item = value
        elif isinstance(value, Mapping):
            payload = dict(value)
            payload.setdefault("workflow_id", workflow_id)
            payload.setdefault("lineage_id", payload.get("commit_id") or entry.entry_id)
            item = RyanContextLineage.from_dict(payload)
        else:
            raise TypeError("commit lineage entries must be objects")
        if item.workflow_id != workflow_id:
            raise WorkflowContextMismatch("commit lineage workflow_id does not match context")
        result.append(item)
    commit_id = str(commit.get("commit_id", "") or entry.entry_id)
    validate_id(commit_id, field="commit_id")
    result.append(
        RyanContextLineage(
            lineage_id=commit_id,
            workflow_id=workflow_id,
            entry_id=entry.entry_id,
            commit_id=commit_id,
            source_agent_uid=entry.source_agent_uid,
            revision=entry.revision,
            upstream_entry_ids=list(entry.upstream_entry_ids),
            created_at=entry.created_at,
        )
    )
    return result


def append_commit(
    upstream: RyanContext | Mapping[str, Any] | None,
    commit: Mapping[str, Any] | RyanContextEntry | None,
    *,
    workflow_id: str | None = None,
) -> RyanContext:
    """将仓库中的最新 Commit 转为 Entry 并追加，输入保持不变。"""
    if upstream is None:
        if not workflow_id:
            raise ValueError("workflow_id is required when upstream is empty")
        base = merge_contexts([], workflow_id=workflow_id)
    else:
        base = _as_context(upstream)
        if workflow_id and base.workflow_id != validate_workflow_id(workflow_id):
            raise WorkflowContextMismatch("upstream workflow_id does not match requested workflow")
    if not commit:
        return base.clone()
    if isinstance(commit, RyanContextEntry):
        entry = commit
        commit_payload: Mapping[str, Any] = entry.to_dict()
    elif isinstance(commit, Mapping):
        commit_payload = commit
        entry = _commit_entry(commit, base.workflow_id)
    else:
        raise TypeError("commit must be a mapping, RyanContextEntry, or null")
    if entry.workflow_id != base.workflow_id:
        raise WorkflowContextMismatch("commit workflow_id does not match upstream workflow")
    incoming = RyanContext(
        workflow_id=base.workflow_id,
        entries=[entry],
        assets=_commit_assets(commit_payload, base.workflow_id),
        lineage=_commit_lineage(commit_payload, entry, base.workflow_id),
    )
    return merge_contexts([base, incoming])


__all__ = ["ContextConflict", "WorkflowContextMismatch", "append_commit", "merge_contexts"]
