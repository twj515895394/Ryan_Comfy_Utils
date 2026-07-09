"""路径组件清洗与「必须落在 root 下」解析，防止 session/export 路径穿越。"""

from __future__ import annotations

import re
from pathlib import Path

# session_id / skill_id / 文件名 stem：字母数字、点、下划线、短横线；允许 Unicode 字母数字
_SAFE_COMPONENT = re.compile(r"^[\w.-]+$", re.UNICODE)
_MAX_COMPONENT_LEN = 128


def sanitize_path_component(name: str, *, field: str = "path") -> str:
    """拒绝空、``.``、``..``、路径分隔符与绝对路径形态。"""
    text = (name or "").strip()
    if not text:
        raise ValueError(f"{field} must be a non-empty path component")
    if text in {".", ".."}:
        raise ValueError(f"{field} must not be '.' or '..'")
    if "/" in text or "\\" in text:
        raise ValueError(f"{field} must not contain path separators: {name!r}")
    if text.startswith("~"):
        raise ValueError(f"{field} must not start with '~': {name!r}")
    if len(text) > _MAX_COMPONENT_LEN:
        raise ValueError(f"{field} exceeds max length {_MAX_COMPONENT_LEN}")
    if not _SAFE_COMPONENT.match(text):
        raise ValueError(f"{field} contains unsafe characters: {name!r}")
    return text


def sanitize_relative_subdir(subdir: str, *, field: str = "output_subdir") -> str:
    """将 ``a/b/c`` 规范为安全相对路径（posix 风格，无前导/尾随斜杠）。"""
    text = (subdir or "").strip().strip("/").strip("\\")
    if not text:
        raise ValueError(f"{field} must be a non-empty relative path")
    parts = re.split(r"[/\\]+", text)
    safe_parts = [sanitize_path_component(p, field=field) for p in parts if p]
    if not safe_parts:
        raise ValueError(f"{field} must be a non-empty relative path")
    return "/".join(safe_parts)


def is_relative_to(path: Path, root: Path) -> bool:
    """Python 3.9+ 兼容的 is_relative_to。"""
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def resolve_under_root(root: Path, *parts: str) -> Path:
    """拼接并 resolve，确保结果仍在 root 之下。"""
    root_resolved = root.resolve()
    candidate = root_resolved.joinpath(*parts).resolve()
    if not is_relative_to(candidate, root_resolved):
        raise ValueError(f"path escapes root {root_resolved}: {candidate}")
    return candidate
