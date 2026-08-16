"""Workflow Agent 文件系统仓库。

所有文件都以 ``workflow_id + agent_uid`` 为作用域；仓库不负责物理删除，
因此删除画布节点不会误删可供恢复或审计的孤儿 Session 数据。
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from ..acp.path_safety import resolve_under_root

from .identity import validate_agent_uid, validate_workflow_id
from .state import AgentState


WORKSPACE_SUBDIR = "acp_workspace"
WORKFLOWS_SUBDIR = "workflows"


def resolve_output_root() -> Path:
    """优先使用 ComfyUI output 目录，否则使用当前目录下的 output。"""
    try:
        import folder_paths  # type: ignore

        return Path(folder_paths.get_output_directory())
    except Exception:
        return Path.cwd() / "output"


def resolve_workspace_root(output_root: str | Path | None = None) -> Path:
    """解析 ``output/acp_workspace``；传入已命名的 workspace 根时不重复追加。"""
    root = Path(output_root) if output_root is not None else resolve_output_root()
    return root if root.name == WORKSPACE_SUBDIR else root / WORKSPACE_SUBDIR


@dataclass(frozen=True, slots=True)
class AgentScopePaths:
    workflow_id: str
    agent_uid: str
    root: Path

    @property
    def pi_session(self) -> Path:
        return self.root / "pi-session.jsonl"

    @property
    def pi_session_path(self) -> Path:
        return self.pi_session

    @property
    def state(self) -> Path:
        return self.root / "state.json"

    @property
    def state_path(self) -> Path:
        return self.state

    @property
    def latest_commit(self) -> Path:
        return self.root / "commits" / "latest.json"

    @property
    def latest_commit_path(self) -> Path:
        return self.latest_commit

    @property
    def lineage(self) -> Path:
        return self.root / "lineage.jsonl"

    @property
    def lineage_path(self) -> Path:
        return self.lineage

    @property
    def assets(self) -> Path:
        return self.root / "assets"

    @property
    def assets_path(self) -> Path:
        return self.assets


class WorkflowAgentRepository:
    """管理单个 Workflow 下 Agent Session 的最小文件布局。"""

    def __init__(self, workspace_root: str | Path | None = None) -> None:
        self.workspace_root = Path(workspace_root) if workspace_root is not None else resolve_workspace_root()
        self.workflows_root = self.workspace_root / WORKFLOWS_SUBDIR

    @classmethod
    def from_output_root(cls, output_root: str | Path | None = None) -> "WorkflowAgentRepository":
        return cls(resolve_workspace_root(output_root))

    def scope_paths(
        self,
        workflow_id: str,
        agent_uid: str,
        *,
        create: bool = True,
    ) -> AgentScopePaths:
        safe_workflow = validate_workflow_id(workflow_id)
        safe_agent = validate_agent_uid(agent_uid)
        root = resolve_under_root(self.workflows_root, safe_workflow, "agents", safe_agent)
        if create:
            (root / "commits").mkdir(parents=True, exist_ok=True)
            (root / "assets").mkdir(parents=True, exist_ok=True)
        return AgentScopePaths(safe_workflow, safe_agent, root)

    # 常用简短别名，供后续 Context / Node / Chat 服务使用。
    scope = scope_paths
    get_scope = scope_paths
    def agent_root(self, workflow_id: str, agent_uid: str, *, create: bool = True) -> Path:
        return self.scope_paths(workflow_id, agent_uid, create=create).root

    def pi_session_path(self, workflow_id: str, agent_uid: str, *, create: bool = True) -> Path:
        return self.scope_paths(workflow_id, agent_uid, create=create).pi_session

    def state_path(self, workflow_id: str, agent_uid: str, *, create: bool = True) -> Path:
        return self.scope_paths(workflow_id, agent_uid, create=create).state

    def latest_commit_path(self, workflow_id: str, agent_uid: str, *, create: bool = True) -> Path:
        return self.scope_paths(workflow_id, agent_uid, create=create).latest_commit

    def lineage_path(self, workflow_id: str, agent_uid: str, *, create: bool = True) -> Path:
        return self.scope_paths(workflow_id, agent_uid, create=create).lineage

    def assets_path(self, workflow_id: str, agent_uid: str, *, create: bool = True) -> Path:
        return self.scope_paths(workflow_id, agent_uid, create=create).assets


    def initialize_scope(
        self,
        workflow_id: str,
        agent_uid: str,
        *,
        state: AgentState | Mapping[str, Any] | None = None,
    ) -> AgentScopePaths:
        paths = self.scope_paths(workflow_id, agent_uid, create=True)
        paths.pi_session.touch(exist_ok=True)
        paths.lineage.touch(exist_ok=True)
        if not paths.latest_commit.exists():
            self._write_json(paths.latest_commit, {})
        if not paths.state.exists():
            initial = state or AgentState(agent_uid=paths.agent_uid, workflow_id=paths.workflow_id)
            self.write_state(paths.workflow_id, paths.agent_uid, initial)
        return paths
    initialize = initialize_scope

    def read_state(self, workflow_id: str, agent_uid: str) -> AgentState:
        paths = self.scope_paths(workflow_id, agent_uid, create=False)
        if not paths.state.exists():
            return AgentState(agent_uid=paths.agent_uid, workflow_id=paths.workflow_id)
        try:
            payload = json.loads(paths.state.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid state JSON: {paths.state}") from exc
        restored = AgentState.from_dict(payload, workflow_id=paths.workflow_id, agent_uid=paths.agent_uid)
        if restored.agent_uid != paths.agent_uid or restored.workflow_id != paths.workflow_id:
            raise ValueError("state identity does not match scope")
        return restored

    def write_state(
        self,
        workflow_id: str,
        agent_uid: str,
        state: AgentState | Mapping[str, Any],
    ) -> AgentState:
        paths = self.scope_paths(workflow_id, agent_uid, create=True)
        normalized = state if isinstance(state, AgentState) else AgentState.from_dict(
            state,
            workflow_id=paths.workflow_id,
            agent_uid=paths.agent_uid,
        )
        if normalized.agent_uid and normalized.agent_uid != paths.agent_uid:
            raise ValueError("state agent_uid does not match scope")
        if normalized.workflow_id and normalized.workflow_id != paths.workflow_id:
            raise ValueError("state workflow_id does not match scope")
        if not normalized.agent_uid:
            normalized.agent_uid = paths.agent_uid
        if not normalized.workflow_id:
            normalized.workflow_id = paths.workflow_id
        self._write_json(paths.state, normalized.to_dict())
        return normalized

    def append_pi_session(self, workflow_id: str, agent_uid: str, entry: Mapping[str, Any]) -> None:
        self._append_jsonl(self.scope_paths(workflow_id, agent_uid).pi_session, entry)

    append_session_entry = append_pi_session

    def read_pi_session(self, workflow_id: str, agent_uid: str) -> list[dict[str, Any]]:
        return self._read_jsonl(self.scope_paths(workflow_id, agent_uid, create=False).pi_session)

    read_session = read_pi_session

    def write_latest_commit(self, workflow_id: str, agent_uid: str, commit: Mapping[str, Any]) -> None:
        paths = self.scope_paths(workflow_id, agent_uid)
        self._write_json(paths.latest_commit, commit)

    def read_latest_commit(self, workflow_id: str, agent_uid: str) -> dict[str, Any]:
        path = self.scope_paths(workflow_id, agent_uid, create=False).latest_commit
        if not path.exists():
            return {}
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("latest commit must be a JSON object")
        return payload

    def append_lineage(self, workflow_id: str, agent_uid: str, entry: Mapping[str, Any]) -> None:
        payload = dict(entry)
        payload.setdefault("recorded_at", datetime.now(timezone.utc).isoformat())
        self._append_jsonl(self.scope_paths(workflow_id, agent_uid).lineage, payload)

    def read_lineage(self, workflow_id: str, agent_uid: str) -> list[dict[str, Any]]:
        return self._read_jsonl(self.scope_paths(workflow_id, agent_uid, create=False).lineage)

    @staticmethod
    def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    @staticmethod
    def _append_jsonl(path: Path, payload: Mapping[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(dict(payload), ensure_ascii=False, separators=(",", ":")) + "\n")

    @staticmethod
    def _read_jsonl(path: Path) -> list[dict[str, Any]]:
        if not path.exists():
            return []
        records: list[dict[str, Any]] = []
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if not line.strip():
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"invalid JSONL at {path}:{line_number}") from exc
            if not isinstance(payload, dict):
                raise ValueError(f"JSONL record must be an object at {path}:{line_number}")
            records.append(payload)
        return records


__all__ = [
    "AgentScopePaths",
    "WORKSPACE_SUBDIR",
    "WORKFLOWS_SUBDIR",
    "WorkflowAgentRepository",
    "resolve_output_root",
    "resolve_workspace_root",
]
