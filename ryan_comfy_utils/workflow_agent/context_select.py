"""将完整 RYAN_CONTEXT 选择为当前 Skill 的模型输入视图。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .artifacts import artifact_outputs, artifact_shots, artifact_summary
from .models import RyanContext, RyanContextEntry


@dataclass(frozen=True, slots=True)
class ContextViewPolicy:
    summary_limit: int = 12_000
    output_limit: int = 4_000
    source_limit: int = 16_000
    total_limit: int = 24_000
    draft_limit: int = 7_000
    message_limit: int = 5_000
    asset_limit: int = 3_000


def _accepted(values: Iterable[str] | None) -> tuple[str, ...]:
    if values is None:
        return ()
    return tuple(str(value) for value in values)


def select_context_entries(
    context: RyanContext,
    accepts_context_kinds: Iterable[str] | None = None,
) -> list[RyanContextEntry]:
    """每个 ``source_agent_uid + kind`` 只返回最高 active revision。"""
    if not isinstance(context, RyanContext):
        raise TypeError("context must be RyanContext")
    accepted = _accepted(accepts_context_kinds)
    latest: dict[tuple[str, str], RyanContextEntry] = {}
    for entry in context.entries:
        if entry.status != "active":
            continue
        key = (entry.source_agent_uid, entry.kind)
        previous = latest.get(key)
        if previous is None or (
            entry.revision,
            entry.created_at,
            entry.entry_id,
        ) > (previous.revision, previous.created_at, previous.entry_id):
            latest[key] = entry
    selected = list(latest.values())
    selected.sort(
        key=lambda entry: (
            0 if "*" in accepted or entry.kind in accepted else 1,
            accepted.index(entry.kind) if entry.kind in accepted else len(accepted),
            entry.source_agent_uid,
            entry.kind,
            entry.entry_id,
        )
    )
    return selected


def _clip(text: str, limit: int) -> str:
    text = str(text or "")
    return text if len(text) <= limit else text[: max(0, limit - 32)] + "\n[... source clipped ...]"


def _selected_lines(entry: RyanContextEntry, output_ids: set[str], shot_ids: set[str], limit: int) -> list[str]:
    lines: list[str] = []
    for output in artifact_outputs(entry):
        if output.output_id in output_ids:
            target_text = "、".join(output.target_ids) if output.target_ids else "未指定对象"
            lines.extend(
                [
                    f"Output [{output.kind}] {output.output_id} / {output.label}:",
                    f"Purpose: {output.purpose or '未指定用途'} / Target: {target_text}",
                    _clip(output.text, limit),
                ]
            )
    for shot in artifact_shots(entry):
        if shot.shot_id in shot_ids:
            lines.extend([f"Shot [{shot.kind}] {shot.shot_id} / {shot.label}:", _clip(shot.prompt, limit)])
    return lines


def render_context_view(
    context: RyanContext,
    accepts_context_kinds: Iterable[str] | None = None,
    *,
    mode: str = "summary",
    selected_output_ids: Iterable[str] | None = None,
    selected_shot_ids: Iterable[str] | None = None,
    policy: ContextViewPolicy | None = None,
) -> str:
    """编译有预算的模型视图；不会修改传入 Context。"""
    if mode not in {"summary", "selected", "full"}:
        raise ValueError("mode must be summary, selected, or full")
    if not isinstance(context, RyanContext):
        raise TypeError("context must be RyanContext")
    view_policy = policy or ContextViewPolicy()
    accepted = _accepted(accepts_context_kinds)
    output_ids = {str(value) for value in (selected_output_ids or ())}
    shot_ids = {str(value) for value in (selected_shot_ids or ())}
    sections = ["# Upstream Context"]
    used = len(sections[0])
    omitted = 0
    for entry in select_context_entries(context, accepted):
        preferred = "*" in accepted or entry.kind in accepted
        if mode == "selected":
            body = ""
            selected = _selected_lines(entry, output_ids, shot_ids, view_policy.output_limit)
            if not selected:
                continue
        else:
            body = entry.content if mode == "full" and preferred else artifact_summary(entry)
            body = _clip(body, view_policy.source_limit if mode == "full" else view_policy.summary_limit)
            selected = _selected_lines(entry, output_ids, shot_ids, view_policy.output_limit)
        block_lines = [
            "",
            f"## [{entry.kind}] {entry.title or entry.source_agent_name or entry.entry_id} / v{entry.revision}",
            f"Source Agent: {entry.source_agent_uid}",
            f"Skill: {entry.skill_id}",
        ]
        if body:
            block_lines.extend(["Summary:" if mode != "full" else "Content:", body])
        if selected:
            block_lines.extend(selected)
        block = "\n".join(block_lines)
        if len(block) > view_policy.source_limit:
            block = _clip(block, view_policy.source_limit)
        if used + len(block) > view_policy.total_limit:
            omitted += 1
            continue
        sections.append(block)
        used += len(block)
    if omitted:
        sections.append(
            f"\n[Context truncated] omitted={omitted} reason=total_limit "
            f"({view_policy.total_limit} chars); use Artifact Selector for a specific output."
        )
    return "\n".join(sections)


def render_selected_context(
    context: RyanContext,
    accepts_context_kinds: Iterable[str] | None = None,
) -> str:
    """兼容旧调用方的摘要视图。"""
    return render_context_view(context, accepts_context_kinds, mode="summary")


select_context = select_context_entries


__all__ = [
    "ContextViewPolicy",
    "render_context_view",
    "render_selected_context",
    "select_context",
    "select_context_entries",
]
