"""创作项目身份：仅本地 creative_project_id，无账号体系。"""
from __future__ import annotations

import re
import uuid

from ..acp.path_safety import sanitize_path_component

_SAFE_ID = re.compile(r"^[\w.-]+$", re.UNICODE)
_MAX_ID_LENGTH = 128


def generate_creative_project_id() -> str:
    return f"creative_{uuid.uuid4().hex}"


def generate_thread_id() -> str:
    return f"thread_{uuid.uuid4().hex}"


def validate_creative_project_id(project_id: str) -> str:
    text = sanitize_path_component(project_id, field="creative_project_id")
    if len(text) > _MAX_ID_LENGTH or not _SAFE_ID.match(text):
        raise ValueError(f"invalid creative_project_id: {project_id!r}")
    return text


def validate_stage_id(stage_id: str) -> str:
    return sanitize_path_component(stage_id, field="stage_id")


def validate_thread_id(thread_id: str) -> str:
    return sanitize_path_component(thread_id, field="thread_id")


__all__ = [
    "generate_creative_project_id",
    "generate_thread_id",
    "validate_creative_project_id",
    "validate_stage_id",
    "validate_thread_id",
]
