"""从 RYAN_CONTEXT 中确定性选择一个结构化产物文本。"""

from __future__ import annotations

from typing import Any

from ..workflow_agent.artifacts import artifact_bundle_from_entry, artifact_outputs, artifact_shots
from ..workflow_agent.context_merge import merge_contexts
from ..workflow_agent.models import RYAN_CONTEXT, RyanContext
_SELECTION_KINDS = {
    "concept_image_prompt": ("concept_image_prompt",),
    "image_prompt": ("image_prompt",),
    "storyboard_prompt": ("storyboard_prompt", "storyboard_sheet_prompt", "shot_prompt"),
    "keyframe_prompt": ("keyframe_prompt",),
    "audio_prompt": ("audio_prompt",),
    "video_prompt": ("video_prompt", "shot_video_prompt"),
}
_SELECTION_ALIASES = {
    "自动选择": "auto",
    "自动读取最新内容": "auto",
    "概念图提示词": "concept_image_prompt",
    "图像提示词": "image_prompt",
    "角色参考图": "image_prompt",
    "场景参考图": "image_prompt",
    "道具参考图": "image_prompt",
    "空间参考图": "image_prompt",
    "分镜提示词": "storyboard_prompt",
    "故事板提示词": "storyboard_prompt",
    "关键帧提示词": "keyframe_prompt",
    "音频提示词": "audio_prompt",
    "视频提示词": "video_prompt",
    "首个结构化产物": "first_output",
    "指定镜头提示词": "shot_prompt",
}
_SHOT_SCOPE_ALIASES = {"全部镜头": "all", "指定镜头": "selected", "指定镜头提示词": "selected"}
_EMPTY_SOURCE_VALUES = {"", "auto", "自动选择来源", "首次运行后可选择上游产物"}
_KIND_DISPLAY = {
    "concept_image_prompt": "概念图提示词",
    "image_prompt": "图像提示词",
    "storyboard_prompt": "分镜提示词",
    "storyboard_sheet_prompt": "分镜表提示词",
    "keyframe_prompt": "关键帧提示词",
    "audio_prompt": "音频提示词",
    "shot_prompt": "镜头提示词",
    "video_prompt": "视频提示词",
    "shot_video_prompt": "镜头视频提示词",
    "continuity_constraint": "连续性约束",
}
class RyanArtifactSelector:
    """只读选择器；没有匹配项时返回空字符串，不猜测其它正文。"""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "source_agent_uid": ("STRING", {"default": ""}),
                "artifact_type": ("STRING", {"default": ""}),
                "output_id": ("STRING", {"default": ""}),
                "shot_id": ("STRING", {"default": ""}),
                "kind": ("STRING", {"default": ""}),
                "revision": ("INT", {"default": 0, "min": 0}),
                # 新字段追加在旧字段后，避免旧 Workflow 的 widgets_values 错位。
                "selection": ("COMBO", {
                    "options": [
                        "自动读取最新内容", "概念图提示词", "图像提示词", "分镜提示词",
                        "关键帧提示词", "音频提示词", "视频提示词", "指定镜头提示词",
                    ],
                    "default": "自动读取最新内容",
                }),
                "source_agent": ("STRING", {"default": "auto"}),
                "shot_scope": ("STRING", {"default": "all"}),
                "purpose": ("STRING", {"default": ""}),
                "target_id": ("STRING", {"default": ""}),
            },
            # 动态镜头选项由前端根据 Context 更新。虽然服务端 Schema 只有占位项，
            # VALIDATE_INPUTS 会让 Queue 跳过 shot 的静态 COMBO 成员检查，
            # 由 run() 按真实 Artifact label 解析最终对象。
            "optional": {
                "context": (RYAN_CONTEXT,),
                "shot": ("COMBO", {
                    "options": ["自动选择镜头"],
                    "default": "自动选择镜头",
                }),
            }
        }

    @classmethod
    def VALIDATE_INPUTS(cls, shot=None):
        # shot 选项由上游 Context 动态产生，不能用静态 options 拒绝合法对象。
        return True

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("text",)
    FUNCTION = "run"
    OUTPUT_NODE = True
    CATEGORY = "Ryan Utils / Agent"

    DESCRIPTION = "默认读取上游最新 Agent 正文；可按图像、分镜、视频提示词或镜头精确选择结构化产物。"

    @staticmethod
    def _entries(context: RyanContext, source_agent_uid: str, artifact_type: str, revision: int):
        entries = []
        for entry in context.entries:
            if entry.status != "active":
                continue
            if source_agent_uid and entry.source_agent_uid != source_agent_uid:
                continue
            if revision and entry.revision != revision:
                continue
            bundle = artifact_bundle_from_entry(entry)
            if bundle is None or (artifact_type and bundle.artifact_type != artifact_type):
                continue
            entries.append((entry, bundle))
        entries.sort(key=lambda item: (item[0].revision, item[0].created_at, item[0].entry_id), reverse=True)
        if not revision:
            # Context 会保留同一 Agent 的历史 Commit；默认只能使用该 Agent 最新版本，
            # 否则旧 Prompt 会在语义选择中泄漏到已更新的 Canon。
            latest_by_agent = {}
            for item in entries:
                latest_by_agent.setdefault(item[0].source_agent_uid, item)
            entries = sorted(
                latest_by_agent.values(),
                key=lambda item: (item[0].revision, item[0].created_at, item[0].entry_id),
                reverse=True,
            )
        return entries

    @classmethod
    def _select_text(
        cls,
        context: RyanContext,
        *,
        source_agent_uid: str,
        artifact_type: str,
        output_id: str,
        shot_id: str,
        kind: str,
        revision: int,
        purpose: str = "",
        target_id: str = "",
        include_outputs: bool = True,
        include_shots: bool = True,
    ) -> str:
        entries = cls._entries(context, source_agent_uid, artifact_type, revision)
        if not entries:
            return ""

        def matches_output(output) -> bool:
            return (
                (not kind or output.kind == kind)
                and (not purpose or output.purpose == purpose)
                and (not target_id or target_id in output.target_ids)
            )

        # Context 同时包含多个阶段；不能只看排序第一的 Agent，否则视频阶段
        # 会遮蔽更早阶段仍可用的角色、分镜或音频 Prompt。
        if output_id:
            for entry, _bundle in entries:
                for output in artifact_outputs(entry) if include_outputs else []:
                    if output.output_id == output_id and matches_output(output):
                        return output.text
            return ""
        if shot_id:
            for entry, _bundle in entries:
                if include_shots:
                    for shot in artifact_shots(entry):
                        if shot.shot_id == shot_id and (not kind or shot.kind == kind):
                            return shot.prompt
                if include_outputs:
                    for output in artifact_outputs(entry):
                        if shot_id in output.target_ids and matches_output(output):
                            return output.text
            return ""

        candidates: list[tuple[int, int, str]] = []
        for entry_index, (entry, _bundle) in enumerate(entries):
            if include_outputs:
                candidates.extend(
                    (output.priority, entry_index, output.text)
                    for output in artifact_outputs(entry)
                    if matches_output(output)
                )
            if include_shots:
                candidates.extend(
                    (shot.priority, entry_index, shot.prompt)
                    for shot in artifact_shots(entry)
                    if not kind or shot.kind == kind
                )
        if candidates:
            candidates.sort(key=lambda item: (item[0], item[1]))
            return candidates[0][2]
        return ""

    @classmethod
    def _select_semantic_text(
        cls,
        context: RyanContext,
        *,
        selection: str,
        source_agent_uid: str,
        shot_id: str,
        revision: int,
        purpose: str = "",
        target_id: str = "",
    ) -> str:
        if selection == "first_output":
            return cls._select_text(
                context,
                source_agent_uid=source_agent_uid,
                artifact_type="",
                output_id="",
                shot_id="",
                kind="",
                purpose=purpose,
                target_id=target_id,
                revision=revision,
            )
        if selection == "shot_prompt":
            # V1 使用 shots；V2 将镜头/Segment Prompt 放在 outputs，并通过 target_ids 关联对象。
            legacy_text = cls._select_text(
                context,
                source_agent_uid=source_agent_uid,
                artifact_type="",
                output_id="",
                shot_id=shot_id,
                kind="shot_prompt",
                revision=revision,
                include_outputs=False,
            )
            if legacy_text:
                return legacy_text
            for kind in ("storyboard_prompt", "storyboard_sheet_prompt", "shot_prompt"):
                text = cls._select_text(
                    context,
                    source_agent_uid=source_agent_uid,
                    artifact_type="",
                    output_id="",
                    shot_id="",
                    kind=kind,
                    purpose=purpose,
                    target_id=shot_id,
                    revision=revision,
                    include_shots=False,
                )
                if text:
                    return text
            return ""

        for kind in _SELECTION_KINDS.get(selection, ()):
            text = cls._select_text(
                context,
                source_agent_uid=source_agent_uid,
                artifact_type="",
                output_id="",
                shot_id="",
                kind=kind,
                purpose=purpose,
                target_id=target_id,
                revision=revision,
                include_outputs=kind != "shot_prompt",
                include_shots=kind == "shot_prompt",
            )
            if text:
                return text
        if selection in {"", "auto"}:
            # 自动读取最新内容的语义是读取 Canonical 正文，不应从多个阶段
            # 按 priority 随机挑出一条 Prompt；Prompt 必须通过显式类型选择。
            entries = [
                entry
                for entry in context.entries
                if entry.status == "active"
                and (not source_agent_uid or entry.source_agent_uid == source_agent_uid)
                and (not revision or entry.revision == revision)
                and entry.content.strip()
            ]
            entries.sort(
                key=lambda entry: (entry.revision, entry.created_at, entry.entry_id),
                reverse=True,
            )
            return entries[0].content if entries else ""
        return ""

    @staticmethod
    def _result(text: str, context: RyanContext | None = None):
        """同时返回连线值、可见预览和最新 Context，供前端刷新动态选项。"""
        ui = {"text": [text]}
        if context is not None:
            ui["context_json"] = [context.to_json()]
        return {"ui": ui, "result": (text,)}

    @staticmethod
    def _revision(value) -> int:
        try:
            return max(0, int(value or 0))
        except (TypeError, ValueError):
            return 0
    def run(
        self,
        source_agent_uid="",
        artifact_type="",
        output_id="",
        shot_id="",
        kind="",
        revision=0,
        selection="auto",
        source_agent="auto",
        shot_scope="all",
        shot="auto",
        purpose="",
        target_id="",
        context=None,
    ):
        if context is None:
            return self._result("")
        if isinstance(context, RyanContext):
            merged = context
        elif isinstance(context, dict):
            merged = RyanContext.from_dict(context)
        else:
            raise TypeError("context must be RYAN_CONTEXT")
        merged = merge_contexts([merged], workflow_id=merged.workflow_id)

        source_uid = str(source_agent_uid or "").strip()
        source_value = str(source_agent or "").strip()
        if not source_uid and source_value not in _EMPTY_SOURCE_VALUES:
            for entry in merged.entries:
                if source_value in {entry.source_agent_uid, entry.source_agent_name}:
                    source_uid = entry.source_agent_uid
        legacy_type = str(artifact_type or "")
        legacy_output = str(output_id or "")
        legacy_shot = str(shot_id or "")
        legacy_kind = str(kind or "")
        requested_purpose = str(purpose or "").strip()
        requested_target = str(target_id or "").strip()
        resolved_revision = self._revision(revision)
        shot_value = str(shot or "").strip()
        empty_shot_values = {
            "",
            "auto",
            "自动选择镜头",
            "自动选择对象",
            "上游暂无可选对象",
            "上游暂无可选镜头",
            "上游暂无可选 Segment",
            "首次运行后可选择镜头",
            "首次运行后可选择对象",
        }

        # 前端对象下拉可能只提交 shot 的展示 label；在此回填 output_id / purpose / target。
        if (
            not legacy_output
            and not legacy_shot
            and shot_value.lower() not in {value.lower() for value in empty_shot_values}
        ):
            for entry in merged.entries:
                if source_uid and entry.source_agent_uid != source_uid:
                    continue
                agent_label = entry.source_agent_name or "上游 Agent"
                for candidate in artifact_outputs(entry):
                    target_text = (
                        " / ".join(candidate.target_ids)
                        if candidate.target_ids
                        else "未指定对象"
                    )
                    purpose_text = f" · 用途：{candidate.purpose}" if candidate.purpose else ""
                    display_label = (
                        f"{agent_label} · "
                        f"{_KIND_DISPLAY.get(candidate.kind, candidate.kind)} · "
                        f"{target_text}{purpose_text}"
                    )
                    aliases = {
                        candidate.output_id,
                        candidate.label,
                        display_label,
                        *candidate.target_ids,
                    }
                    if shot_value not in aliases and not any(
                        token and token in shot_value
                        for token in (candidate.output_id, candidate.label, *candidate.target_ids)
                    ):
                        continue
                    legacy_output = candidate.output_id
                    legacy_kind = legacy_kind or candidate.kind
                    legacy_type = legacy_type or (
                        (artifact_bundle_from_entry(entry).artifact_type
                         if artifact_bundle_from_entry(entry)
                         else "")
                    )
                    if not source_uid:
                        source_uid = entry.source_agent_uid
                    if not requested_purpose:
                        requested_purpose = candidate.purpose or ""
                    if not requested_target and candidate.target_ids:
                        requested_target = candidate.target_ids[0]
                    break
                if legacy_output:
                    break
                for candidate in artifact_shots(entry):
                    aliases = {candidate.shot_id, candidate.label}
                    if shot_value not in aliases and candidate.shot_id not in shot_value:
                        continue
                    legacy_shot = candidate.shot_id
                    legacy_kind = legacy_kind or candidate.kind
                    if not source_uid:
                        source_uid = entry.source_agent_uid
                    break
                if legacy_shot:
                    break

        if legacy_type or legacy_output or legacy_shot or legacy_kind or requested_purpose or requested_target:
            return self._result(
                self._select_text(
                    merged,
                    source_agent_uid=source_uid,
                    artifact_type=legacy_type,
                    output_id=legacy_output,
                    shot_id=legacy_shot,
                    kind=legacy_kind,
                    purpose=requested_purpose,
                    target_id=requested_target,
                    revision=resolved_revision,
                ),
                merged,
            )
        selection_key = _SELECTION_ALIASES.get(
            str(selection or "").strip(),
            str(selection or "auto").strip(),
        )
        scope_key = _SHOT_SCOPE_ALIASES.get(
            str(shot_scope or "").strip(),
            str(shot_scope or "all").strip(),
        )
        selected_shot = ""
        if scope_key == "selected" and shot_value.lower() not in {
            value.lower() for value in empty_shot_values
        }:
            resolved_shot = ""
            for entry in merged.entries:
                for candidate in artifact_shots(entry):
                    if shot_value in {candidate.shot_id, candidate.label}:
                        resolved_shot = candidate.shot_id
                        break
                if resolved_shot:
                    break
                for candidate in artifact_outputs(entry):
                    if shot_value != candidate.label and shot_value not in candidate.target_ids:
                        continue
                    resolved_shot = shot_value if shot_value in candidate.target_ids else next(
                        (
                            target_id
                            for target_id in candidate.target_ids
                            if target_id.startswith(("SHOT_", "SEG_"))
                        ),
                        "",
                    )
                    if resolved_shot:
                        break
                if resolved_shot:
                    break
            selected_shot = resolved_shot
        if selection_key == "shot_prompt" and scope_key == "selected" and not selected_shot:
            return self._result("", merged)
        return self._result(
            self._select_semantic_text(
                merged,
                selection=selection_key,
                source_agent_uid=source_uid,
                shot_id=selected_shot,
                purpose=requested_purpose,
                target_id=requested_target,
                revision=resolved_revision,
            ),
            merged,
        )


__all__ = ["RyanArtifactSelector"]
