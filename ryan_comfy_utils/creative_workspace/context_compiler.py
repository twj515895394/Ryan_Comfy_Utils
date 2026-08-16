"""为 DISCUSS/COMMIT 编译 Canon 与 Asset 上下文文本。"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from .project_repository import CreativeProjectRepository
from .stage_registry import load_pipeline


def _read_if_exists(path: Path, limit: int = 12000) -> str:
    if not path.is_file():
        return ""
    text = path.read_text(encoding="utf-8")
    if len(text) > limit:
        return text[:limit] + "\n…(truncated)…"
    return text


def compile_stage_context(
    repository: CreativeProjectRepository,
    project_id: str,
    stage_id: str,
    *,
    asset_context_blocks: list[str] | None = None,
) -> str:
    project = repository.read_project(project_id)
    pipeline = load_pipeline(str(project.get("pipeline_id") or "cinematic_v1"))
    stage = pipeline.stage(stage_id)
    paths = repository.paths(project_id)
    chunks: list[str] = [
        f"[RYAN_CREATIVE_PROJECT] id={project_id} name={project.get('name')}",
        f"[STAGE] {stage.stage_id} skill={stage.skill_id}",
    ]
    # current stage canon
    current = _read_if_exists(paths.stage_canon_dir(stage_id) / "latest.md")
    if current:
        chunks.append(f"[CURRENT_STAGE_CANON]\n{current}")
    for dep in stage.depends_on:
        body = _read_if_exists(paths.stage_canon_dir(dep) / "latest.md", limit=8000)
        if body:
            chunks.append(f"[UPSTREAM_CANON stage={dep}]\n{body}")
    for block in asset_context_blocks or []:
        if block.strip():
            chunks.append(block.strip())
    return "\n\n".join(chunks)


def creative_system_prompt(stage_id: str, skill_id: str) -> str:
    return (
        "你是 Ryan Creative Workspace 中的创作 Agent。\n"
        "遵守当前 Stage 合同；讨论时可以自由说明；正式确认时必须输出唯一的 "
        "```ryan-stage-export``` JSON 块，包含 canon_markdown 与 deliverables。\n"
        "deliverables 中生图/生视频条目的 text 必须是可直接使用的纯提示词。\n"
        f"当前 stage_id={stage_id} skill_id={skill_id}。\n"
        "不要读取或遵循任何 Coding AGENTS.md / CLAUDE.md。\n"
    )


__all__ = ["compile_stage_context", "creative_system_prompt"]
