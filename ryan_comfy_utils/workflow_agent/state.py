"""Ryan Workflow Agent 的可恢复业务状态。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from .identity import validate_agent_uid, validate_workflow_id


@dataclass(slots=True)
class AgentState:
    """落盘于 ``state.json`` 的最小状态集合。"""

    skill_id: str = ""
    agent_name: str = ""
    agent_uid: str = ""
    draft: Any = ""
    status: str = "idle"
    commit_revision: int = 0
    latest_entry_id: str | None = None
    workflow_id: str | None = None

    def __post_init__(self) -> None:
        if self.agent_uid:
            self.agent_uid = validate_agent_uid(self.agent_uid)
        if self.workflow_id:
            self.workflow_id = validate_workflow_id(self.workflow_id)
        if not isinstance(self.commit_revision, int) or isinstance(self.commit_revision, bool):
            raise TypeError("commit_revision must be an integer")
        if self.commit_revision < 0:
            raise ValueError("commit_revision must not be negative")
        for field in ("skill_id", "agent_name", "status"):
            value = getattr(self, field)
            if not isinstance(value, str):
                raise TypeError(f"{field} must be a string")

    def to_dict(self) -> dict[str, Any]:
        """转换为 JSON-safe mapping，字段名保持持久化合同稳定。"""
        payload: dict[str, Any] = {
            "skill_id": self.skill_id,
            "agent_name": self.agent_name,
            "agent_uid": self.agent_uid,
            "draft": self.draft,
            "status": self.status,
            "commit_revision": self.commit_revision,
            "latest_entry_id": self.latest_entry_id,
        }
        if self.workflow_id is not None:
            payload["workflow_id"] = self.workflow_id
        return payload

    def __getitem__(self, key: str) -> Any:
        return self.to_dict()[key]

    def get(self, key: str, default: Any = None) -> Any:
        return self.to_dict().get(key, default)

    @classmethod
    def from_dict(
        cls,
        payload: Mapping[str, Any],
        *,
        workflow_id: str | None = None,
        agent_uid: str | None = None,
    ) -> "AgentState":
        """从 JSON 对象恢复状态；未知字段忽略以允许后续扩展。"""
        if not isinstance(payload, Mapping):
            raise TypeError("state payload must be a mapping")
        resolved_workflow = payload.get("workflow_id", workflow_id)
        resolved_agent = payload.get("agent_uid", agent_uid) or ""
        return cls(
            skill_id=payload.get("skill_id", ""),
            agent_name=payload.get("agent_name", ""),
            agent_uid=resolved_agent,
            draft=payload.get("draft", ""),
            status=payload.get("status", "idle"),
            commit_revision=payload.get("commit_revision", 0),
            latest_entry_id=payload.get("latest_entry_id"),
            workflow_id=resolved_workflow,
        )


__all__ = ["AgentState"]
