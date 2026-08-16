"""确认 / Reopen / STALE。"""
from __future__ import annotations

import threading
import uuid
from typing import Any, Callable

from .identity import validate_stage_id
from .project_repository import CreativeProjectRepository
from .stage_export import (
    StageExportError,
    check_ready,
    parse_stage_export,
    write_stage_export,
)
from .stage_registry import load_pipeline


class StageServiceError(RuntimeError):
    """阶段服务失败。"""


class CreativeStageService:
    def __init__(
        self,
        repository: CreativeProjectRepository | None = None,
        *,
        commit_runner: Callable[..., str] | None = None,
    ) -> None:
        self.repository = repository or CreativeProjectRepository()
        self.commit_runner = commit_runner
        self._locks: dict[tuple[str, str], threading.RLock] = {}
        self._guard = threading.RLock()

    def _stage_lock(self, project_id: str, stage_id: str) -> threading.RLock:
        key = (project_id, stage_id)
        with self._guard:
            lock = self._locks.get(key)
            if lock is None:
                lock = threading.RLock()
                self._locks[key] = lock
            return lock

    def list_stages(self, project_id: str) -> list[dict[str, Any]]:
        project = self.repository.read_project(project_id)
        pipeline = load_pipeline(str(project.get("pipeline_id") or "cinematic_v1"))
        state = self.repository.read_state(project_id)
        stages_state = state.get("stages") or {}
        rows: list[dict[str, Any]] = []
        for spec in pipeline.stages:
            row = dict(stages_state.get(spec.stage_id) or {})
            row.setdefault("stage_id", spec.stage_id)
            row.setdefault("skill_id", spec.skill_id)
            row.setdefault("status", "NOT_STARTED")
            row.setdefault("revision", 0)
            row.setdefault("stale_causes", [])
            row["display_name"] = spec.display_name
            row["depends_on"] = list(spec.depends_on)
            row["optional"] = spec.optional
            rows.append(row)
        return rows

    def get_stage(self, project_id: str, stage_id: str) -> dict[str, Any]:
        stage = validate_stage_id(stage_id)
        for row in self.list_stages(project_id):
            if row["stage_id"] == stage:
                return row
        raise KeyError(stage_id)

    def mark_draft(self, project_id: str, stage_id: str) -> dict[str, Any]:
        stage = validate_stage_id(stage_id)
        state = self.repository.read_state(project_id)
        row = state.setdefault("stages", {}).setdefault(stage, {})
        if row.get("status") not in {"LOCKED", "STALE"}:
            row["status"] = "DRAFT"
        self.repository.write_state(project_id, state)
        return self.get_stage(project_id, stage)

    def evaluate_ready(self, project_id: str, stage_id: str, thread_id: str = "") -> dict[str, Any]:
        stage = validate_stage_id(stage_id)
        pipeline = load_pipeline()
        spec = pipeline.stage(stage)
        state = self.repository.read_state(project_id)
        stage_state = (state.get("stages") or {}).get(stage) or {}
        tid = thread_id or str(stage_state.get("current_thread_id") or "")
        if not tid:
            tid = self.repository.ensure_main_thread(project_id, stage)
        text = self._last_complete_assistant_text(project_id, stage, tid)
        ready = check_ready(text, spec) if text else check_ready("", spec)
        # persist READY only as soft signal when draft exists
        if ready.ready and stage_state.get("status") not in {"LOCKED", "STALE"}:
            state = self.repository.read_state(project_id)
            state.setdefault("stages", {}).setdefault(stage, {})["status"] = "READY"
            self.repository.write_state(project_id, state)
        return {
            "ready": ready.ready,
            "reason": ready.reason,
            "thread_id": tid,
            "has_export": ready.payload is not None,
        }

    def _last_complete_assistant_text(self, project_id: str, stage_id: str, thread_id: str) -> str:
        records = self.repository.read_thread_records(project_id, stage_id, thread_id)
        for record in reversed(records):
            if record.get("role") != "assistant":
                continue
            if record.get("status") in {"streaming", "stopped", "error"}:
                continue
            content = str(record.get("content") or "")
            if content.strip():
                return content
        return ""

    def confirm(
        self,
        project_id: str,
        stage_id: str,
        *,
        thread_id: str = "",
        mode: str = "commit",
        user_message: str = "",
    ) -> dict[str, Any]:
        stage = validate_stage_id(stage_id)
        if mode not in {"commit", "draft"}:
            raise StageServiceError("mode must be commit|draft")
        with self._stage_lock(project_id, stage):
            pipeline = load_pipeline()
            spec = pipeline.stage(stage)
            state = self.repository.read_state(project_id)
            stage_state = state.setdefault("stages", {}).setdefault(stage, {})
            tid = thread_id or str(stage_state.get("current_thread_id") or "")
            if not tid:
                tid = self.repository.ensure_main_thread(project_id, stage)
            draft_text = self._last_complete_assistant_text(project_id, stage, tid)
            export_text = draft_text
            if mode == "draft":
                ready = check_ready(draft_text, spec)
                if not ready.ready or ready.payload is None:
                    raise StageServiceError(ready.reason or "draft is not READY")
                payload = ready.payload
            else:
                if self.commit_runner is None:
                    # 无 runner 时若草稿已合法则允许（测试/离线）
                    ready = check_ready(draft_text, spec)
                    if not ready.ready or ready.payload is None:
                        raise StageServiceError(
                            ready.reason or "commit_runner missing and draft not READY"
                        )
                    payload = ready.payload
                    export_text = draft_text
                else:
                    export_text = self.commit_runner(
                        project_id=project_id,
                        stage_id=stage,
                        thread_id=tid,
                        skill_id=spec.skill_id,
                        user_message=user_message or "请输出正式 ryan-stage-export 确认结果。",
                        draft_text=draft_text,
                    )
                    ready = check_ready(export_text, spec)
                    if not ready.ready or ready.payload is None:
                        raise StageServiceError(ready.reason or "commit export invalid")
                    payload = ready.payload
                    # persist commit assistant message
                    self.repository.append_thread_record(
                        project_id,
                        stage,
                        tid,
                        {
                            "role": "assistant",
                            "content": export_text,
                            "status": "complete",
                            "message_id": f"msg_{uuid.uuid4().hex}",
                            "request_id": f"req_{uuid.uuid4().hex}",
                            "kind": "commit",
                        },
                    )

            revision = int(stage_state.get("revision") or 0) + 1
            write_info = write_stage_export(
                self.repository,
                project_id,
                stage,
                payload,
                revision=revision,
            )
            entry_id = f"entry_{uuid.uuid4().hex}"
            stage_state["status"] = "LOCKED"
            stage_state["revision"] = revision
            stage_state["latest_entry_id"] = entry_id
            stage_state["stale_causes"] = []
            stage_state["current_thread_id"] = tid
            self._mark_dependents_stale(state, stage, revision, entry_id)
            self.repository.write_state(project_id, state)
            project = self.repository.read_project(project_id)
            project["current_stage"] = stage
            self.repository.write_project(project_id, project)
            return {
                "status": "ok",
                "mode": mode,
                "stage": self.get_stage(project_id, stage),
                "write": write_info,
                "thread_id": tid,
                "entry_id": entry_id,
            }

    def _mark_dependents_stale(
        self,
        state: dict[str, Any],
        upstream_stage_id: str,
        upstream_revision: int,
        upstream_entry_id: str,
    ) -> None:
        pipeline = load_pipeline()
        stages = state.setdefault("stages", {})
        for dep_id in pipeline.dependents_of(upstream_stage_id):
            row = stages.setdefault(dep_id, {"stage_id": dep_id})
            status = str(row.get("status") or "NOT_STARTED")
            if status in {"NOT_STARTED"}:
                continue
            if int(row.get("revision") or 0) <= 0 and status not in {"LOCKED", "STALE", "READY", "DRAFT"}:
                continue
            # only mark if downstream has been touched or locked
            if status in {"NOT_STARTED"}:
                continue
            causes = list(row.get("stale_causes") or [])
            cause = {
                "upstream_stage_id": upstream_stage_id,
                "upstream_revision": upstream_revision,
                "upstream_entry_id": upstream_entry_id,
            }
            if cause not in causes:
                causes.append(cause)
            row["stale_causes"] = causes
            if status in {"LOCKED", "READY", "DRAFT", "STALE", "ERROR"}:
                row["status"] = "STALE"

    def reopen(self, project_id: str, stage_id: str) -> dict[str, Any]:
        stage = validate_stage_id(stage_id)
        with self._stage_lock(project_id, stage):
            state = self.repository.read_state(project_id)
            row = state.setdefault("stages", {}).setdefault(stage, {})
            if str(row.get("status")) not in {"LOCKED", "STALE"}:
                raise StageServiceError("only LOCKED or STALE stages can reopen")
            row["status"] = "DRAFT"
            self.repository.write_state(project_id, state)
            return self.get_stage(project_id, stage)

    def stage_is_stale(self, project_id: str, stage_id: str) -> bool:
        row = self.get_stage(project_id, stage_id)
        return str(row.get("status")) == "STALE"

    def stale_stages_for_document(self, project_id: str, relative_path: str) -> list[str]:
        rel = relative_path.replace("\\", "/").lstrip("/")
        parts = rel.split("/")
        if len(parts) < 2:
            return []
        # canon/<stage>/... or deliverables/<stage>/...
        if parts[0] not in {"canon", "deliverables"}:
            return []
        stage_id = parts[1]
        try:
            if self.stage_is_stale(project_id, stage_id):
                return [stage_id]
        except Exception:
            return []
        return []


__all__ = ["StageServiceError", "CreativeStageService"]
