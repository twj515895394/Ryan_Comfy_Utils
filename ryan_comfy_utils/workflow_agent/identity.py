"""Workflow / Agent 身份生成与持久化边界。"""

from __future__ import annotations

import re
import uuid
from collections.abc import MutableMapping
from typing import Any


_RYAN_AGENT_KEY = "ryan_agent"
_SAFE_ID = re.compile(r"^[\w.-]+$", re.UNICODE)
_MAX_ID_LENGTH = 128


def _metadata_container(workflow_or_extra: MutableMapping[str, Any]) -> MutableMapping[str, Any]:
    """返回 ``extra.ryan_agent`` 的父级，兼容传入 workflow 或 extra。"""
    if not isinstance(workflow_or_extra, MutableMapping):
        raise TypeError("workflow metadata must be a mutable mapping")
    extra = workflow_or_extra.get("extra")
    if isinstance(extra, MutableMapping):
        return extra
    return workflow_or_extra


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex}"


def generate_workflow_id() -> str:
    """生成新的 Workflow 身份；不读取或修改任何外部状态。"""
    return _new_id("wf")


def generate_agent_uid() -> str:
    """生成新的 Agent 节点身份；不读取或修改任何外部状态。"""
    return _new_id("agent")


def validate_id(value: str, *, field: str = "id") -> str:
    """校验一个可安全作为单一路径组件的持久化 ID。"""
    if not isinstance(value, str):
        raise TypeError(f"{field} must be a string")
    text = value.strip()
    if not text:
        raise ValueError(f"{field} must be a non-empty path component")
    if text != value:
        raise ValueError(f"{field} must not contain leading or trailing whitespace")
    if text in {".", ".."}:
        raise ValueError(f"{field} must not be '.' or '..'")
    if "/" in text or "\\" in text:
        raise ValueError(f"{field} must not contain path separators")
    if text.startswith("~"):
        raise ValueError(f"{field} must not start with '~'")
    if len(text) > _MAX_ID_LENGTH:
        raise ValueError(f"{field} exceeds max length {_MAX_ID_LENGTH}")
    if not _SAFE_ID.fullmatch(text):
        raise ValueError(f"{field} contains unsafe characters")
    return text


def validate_workflow_id(workflow_id: str) -> str:
    return validate_id(workflow_id, field="workflow_id")


def validate_agent_uid(agent_uid: str) -> str:
    return validate_id(agent_uid, field="agent_uid")


def get_workflow_id(workflow_or_extra: MutableMapping[str, Any]) -> str | None:
    """读取 ``extra.ryan_agent.workflow_id``，缺失时返回 ``None``。"""
    extra = _metadata_container(workflow_or_extra)
    ryan_agent = extra.get(_RYAN_AGENT_KEY)
    if not isinstance(ryan_agent, MutableMapping):
        return None
    value = ryan_agent.get("workflow_id")
    if value is None:
        return None
    return validate_workflow_id(value)


def ensure_workflow_id(workflow_or_extra: MutableMapping[str, Any]) -> str:
    """读取或生成并持久化 Workflow ID。

    仅在缺少 ID 时修改 metadata；改名只要复用同一 metadata 就不会改变 ID。
    """
    extra = _metadata_container(workflow_or_extra)
    ryan_agent = extra.get(_RYAN_AGENT_KEY)
    if ryan_agent is None:
        ryan_agent = {}
        extra[_RYAN_AGENT_KEY] = ryan_agent
    if not isinstance(ryan_agent, MutableMapping):
        raise TypeError("extra.ryan_agent must be a mapping")
    value = ryan_agent.get("workflow_id")
    if value is None:
        value = generate_workflow_id()
        ryan_agent["workflow_id"] = value
    return validate_workflow_id(value)


def workflow_id_for_save_as(_source_workflow_id: str | None = None) -> str:
    """为 Save As / Duplicate 生成全新的 Workflow ID。"""
    if _source_workflow_id is not None:
        validate_workflow_id(_source_workflow_id)
    return generate_workflow_id()


def agent_uid_for_duplicate(_source_agent_uid: str | None = None) -> str:
    """为复制 Agent 或切换 Skill 生成全新的 Agent UID。"""
    if _source_agent_uid is not None:
        validate_agent_uid(_source_agent_uid)
    return generate_agent_uid()


# 语义别名，便于节点和后续服务按领域词汇导入。
new_workflow_id = generate_workflow_id
new_agent_uid = generate_agent_uid
duplicate_workflow_id = workflow_id_for_save_as
duplicate_agent_uid = agent_uid_for_duplicate

__all__ = [
    "agent_uid_for_duplicate",
    "duplicate_agent_uid",
    "duplicate_workflow_id",
    "ensure_workflow_id",
    "generate_agent_uid",
    "generate_workflow_id",
    "get_workflow_id",
    "new_agent_uid",
    "new_workflow_id",
    "validate_agent_uid",
    "validate_id",
    "validate_workflow_id",
    "workflow_id_for_save_as",
]
