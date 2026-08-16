"""创作项目本地文件系统仓库。"""
from __future__ import annotations

import json
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..acp.path_safety import resolve_under_root
from .identity import (
    generate_creative_project_id,
    generate_thread_id,
    validate_creative_project_id,
    validate_stage_id,
    validate_thread_id,
)
from .stage_registry import PIPELINE_ID, load_pipeline


WORKSPACE_DIRNAME = "ryan_creative_workspace"
PROJECTS_DIRNAME = "projects"
GLOBAL_STATE_NAME = "global_state.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def resolve_output_root() -> Path:
    try:
        import folder_paths  # type: ignore

        return Path(folder_paths.get_output_directory())
    except Exception:
        return Path.cwd() / "output"


def resolve_creative_root(output_root: str | Path | None = None) -> Path:
    root = Path(output_root) if output_root is not None else resolve_output_root()
    if root.name == WORKSPACE_DIRNAME:
        return root
    return root / WORKSPACE_DIRNAME


def _read_json(path: Path, default: Any) -> Any:
    if not path.is_file():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


@dataclass(frozen=True, slots=True)
class ProjectPaths:
    project_id: str
    root: Path

    @property
    def project_json(self) -> Path:
        return self.root / "project.json"

    @property
    def state_json(self) -> Path:
        return self.root / "state.json"

    @property
    def canon(self) -> Path:
        return self.root / "canon"

    @property
    def deliverables(self) -> Path:
        return self.root / "deliverables"

    @property
    def threads(self) -> Path:
        return self.root / "threads"

    @property
    def refs(self) -> Path:
        return self.root / "refs"

    @property
    def cache(self) -> Path:
        return self.root / "cache"

    def stage_canon_dir(self, stage_id: str) -> Path:
        return self.canon / validate_stage_id(stage_id)

    def stage_deliverables_dir(self, stage_id: str) -> Path:
        return self.deliverables / validate_stage_id(stage_id)

    def thread_path(self, stage_id: str, thread_id: str) -> Path:
        stage = validate_stage_id(stage_id)
        thread = validate_thread_id(thread_id)
        return self.threads / stage / f"{thread}.jsonl"


class CreativeProjectRepository:
    """本地创作项目目录；无成员/鉴权。"""

    def __init__(self, root: str | Path | None = None) -> None:
        self.root = resolve_creative_root(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.projects_root = self.root / PROJECTS_DIRNAME
        self.projects_root.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()

    def _global_state_path(self) -> Path:
        return self.root / GLOBAL_STATE_NAME

    def read_global_state(self) -> dict[str, Any]:
        payload = _read_json(self._global_state_path(), {})
        if not isinstance(payload, dict):
            return {}
        return payload

    def write_global_state(self, payload: dict[str, Any]) -> dict[str, Any]:
        data = dict(payload)
        data["updated_at"] = _utc_now()
        _write_json(self._global_state_path(), data)
        return data

    def get_current_project_id(self) -> str | None:
        value = self.read_global_state().get("current_creative_project_id")
        if not value:
            return None
        try:
            return validate_creative_project_id(str(value))
        except ValueError:
            return None

    def set_current_project_id(self, project_id: str | None) -> None:
        state = self.read_global_state()
        if project_id is None:
            state.pop("current_creative_project_id", None)
        else:
            state["current_creative_project_id"] = validate_creative_project_id(project_id)
        self.write_global_state(state)

    def paths(self, project_id: str) -> ProjectPaths:
        pid = validate_creative_project_id(project_id)
        root = resolve_under_root(self.projects_root, pid)
        return ProjectPaths(project_id=pid, root=root)

    def _default_stage_state(self, pipeline_id: str = PIPELINE_ID) -> dict[str, Any]:
        pipeline = load_pipeline(pipeline_id)
        stages: dict[str, Any] = {}
        for stage in pipeline.stages:
            stages[stage.stage_id] = {
                "stage_id": stage.stage_id,
                "skill_id": stage.skill_id,
                "status": "NOT_STARTED",
                "revision": 0,
                "latest_entry_id": "",
                "depends_on": list(stage.depends_on),
                "stale_causes": [],
                "current_thread_id": "",
                "main_thread_id": "",
            }
        return {
            "schema_version": 1,
            "pipeline_id": pipeline_id,
            "stages": stages,
            "threads": {},
        }

    def create_project(self, name: str = "", *, pipeline_id: str = PIPELINE_ID) -> dict[str, Any]:
        with self._lock:
            project_id = generate_creative_project_id()
            paths = self.paths(project_id)
            paths.root.mkdir(parents=True, exist_ok=False)
            now = _utc_now()
            project = {
                "schema_version": 1,
                "project_id": project_id,
                "name": (name or project_id).strip() or project_id,
                "pipeline_id": pipeline_id,
                "current_stage": "creative",
                "created_at": now,
                "updated_at": now,
                "external_bindings": {"comfytv_project_id": None},
            }
            state = self._default_stage_state(pipeline_id)
            # bootstrap main thread per stage lazily on first chat; store empty threads map
            for directory in (
                paths.canon,
                paths.deliverables,
                paths.threads,
                paths.refs,
                paths.cache,
            ):
                directory.mkdir(parents=True, exist_ok=True)
            for stage in load_pipeline(pipeline_id).stages:
                paths.stage_canon_dir(stage.stage_id).mkdir(parents=True, exist_ok=True)
                paths.stage_deliverables_dir(stage.stage_id).mkdir(parents=True, exist_ok=True)
                (paths.threads / stage.stage_id).mkdir(parents=True, exist_ok=True)
            _write_json(paths.project_json, project)
            _write_json(paths.state_json, state)
            _write_json(paths.refs / "assets.json", {"assets": []})
            self.set_current_project_id(project_id)
            return project

    def project_exists(self, project_id: str) -> bool:
        return self.paths(project_id).project_json.is_file()

    def read_project(self, project_id: str) -> dict[str, Any]:
        paths = self.paths(project_id)
        if not paths.project_json.is_file():
            raise FileNotFoundError(f"creative project not found: {project_id}")
        payload = _read_json(paths.project_json, {})
        if not isinstance(payload, dict):
            raise ValueError("invalid project.json")
        return payload

    def write_project(self, project_id: str, project: dict[str, Any]) -> dict[str, Any]:
        paths = self.paths(project_id)
        data = dict(project)
        data["project_id"] = validate_creative_project_id(project_id)
        data["updated_at"] = _utc_now()
        _write_json(paths.project_json, data)
        return data

    def list_projects(self) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        if not self.projects_root.is_dir():
            return rows
        for child in sorted(self.projects_root.iterdir(), key=lambda p: p.name):
            if not child.is_dir():
                continue
            project_file = child / "project.json"
            if not project_file.is_file():
                continue
            try:
                rows.append(self.read_project(child.name))
            except Exception:
                continue
        return rows

    def open_project(self, project_id: str) -> dict[str, Any]:
        project = self.read_project(project_id)
        self.set_current_project_id(project_id)
        return project

    def reset_workspace(self, name: str = "") -> dict[str, Any]:
        """新 id + 切换 current；旧目录保留。"""
        return self.create_project(name=name or "新工作区")

    def read_state(self, project_id: str) -> dict[str, Any]:
        paths = self.paths(project_id)
        if not paths.state_json.is_file():
            raise FileNotFoundError(f"state missing for project: {project_id}")
        payload = _read_json(paths.state_json, {})
        if not isinstance(payload, dict):
            raise ValueError("invalid state.json")
        return payload

    def write_state(self, project_id: str, state: dict[str, Any]) -> dict[str, Any]:
        paths = self.paths(project_id)
        data = dict(state)
        data["updated_at"] = _utc_now()
        _write_json(paths.state_json, data)
        return data

    def ensure_main_thread(self, project_id: str, stage_id: str) -> str:
        stage = validate_stage_id(stage_id)
        state = self.read_state(project_id)
        stages = state.setdefault("stages", {})
        stage_state = stages.setdefault(stage, {})
        main_id = str(stage_state.get("main_thread_id") or "").strip()
        if main_id:
            stage_state.setdefault("current_thread_id", main_id)
            self.write_state(project_id, state)
            return main_id
        thread_id = generate_thread_id()
        stage_state["main_thread_id"] = thread_id
        stage_state["current_thread_id"] = thread_id
        threads = state.setdefault("threads", {})
        threads[thread_id] = {
            "thread_id": thread_id,
            "stage_id": stage,
            "title": "主讨论",
            "is_main": True,
            "created_at": _utc_now(),
        }
        paths = self.paths(project_id)
        path = paths.thread_path(stage, thread_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            path.write_text("", encoding="utf-8")
        self.write_state(project_id, state)
        return thread_id

    def create_thread(self, project_id: str, stage_id: str, title: str = "") -> dict[str, Any]:
        stage = validate_stage_id(stage_id)
        self.ensure_main_thread(project_id, stage)
        thread_id = generate_thread_id()
        state = self.read_state(project_id)
        record = {
            "thread_id": thread_id,
            "stage_id": stage,
            "title": (title or "讨论").strip() or "讨论",
            "is_main": False,
            "created_at": _utc_now(),
        }
        state.setdefault("threads", {})[thread_id] = record
        state.setdefault("stages", {}).setdefault(stage, {})["current_thread_id"] = thread_id
        paths = self.paths(project_id)
        path = paths.thread_path(stage, thread_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("", encoding="utf-8")
        self.write_state(project_id, state)
        return record

    def set_current_thread(self, project_id: str, stage_id: str, thread_id: str) -> None:
        stage = validate_stage_id(stage_id)
        tid = validate_thread_id(thread_id)
        state = self.read_state(project_id)
        threads = state.get("threads") or {}
        if tid not in threads:
            raise FileNotFoundError(f"thread not found: {thread_id}")
        if str(threads[tid].get("stage_id")) != stage:
            raise ValueError("thread does not belong to stage")
        state.setdefault("stages", {}).setdefault(stage, {})["current_thread_id"] = tid
        self.write_state(project_id, state)

    def append_thread_record(self, project_id: str, stage_id: str, thread_id: str, record: dict[str, Any]) -> None:
        path = self.paths(project_id).thread_path(stage_id, thread_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")

    def read_thread_records(self, project_id: str, stage_id: str, thread_id: str) -> list[dict[str, Any]]:
        path = self.paths(project_id).thread_path(stage_id, thread_id)
        if not path.is_file():
            return []
        rows: list[dict[str, Any]] = []
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(payload, dict):
                rows.append(payload)
        return rows

    def read_asset_refs(self, project_id: str) -> list[dict[str, Any]]:
        path = self.paths(project_id).refs / "assets.json"
        payload = _read_json(path, {"assets": []})
        assets = payload.get("assets") if isinstance(payload, dict) else []
        return list(assets) if isinstance(assets, list) else []

    def write_asset_refs(self, project_id: str, assets: list[dict[str, Any]]) -> list[dict[str, Any]]:
        path = self.paths(project_id).refs / "assets.json"
        _write_json(path, {"assets": assets})
        return assets


__all__ = [
    "WORKSPACE_DIRNAME",
    "CreativeProjectRepository",
    "ProjectPaths",
    "resolve_creative_root",
    "resolve_output_root",
]
