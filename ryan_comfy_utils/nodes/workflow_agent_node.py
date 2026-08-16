"""Ryan Workflow Agent 的确定性 Queue 节点。

Queue 阶段只读取 Context 和仓库中的 latest Commit；聊天、Pi 与 LLM 只属于
Interactive Plane，绝不从这里启动。
"""

from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory

from ..acp.skill_loader import resolve_skill_root
from ..workflow_agent.artifacts import artifact_outputs
from ..workflow_agent.assets import WorkflowAgentAssetStore
from ..workflow_agent.context_merge import append_commit, merge_contexts
from ..workflow_agent.identity import validate_agent_uid, validate_workflow_id
from ..workflow_agent.models import RYAN_CONTEXT, RyanContext
from ..workflow_agent.repository import WorkflowAgentRepository


_CONTEXT_INPUTS = tuple(f"context_{index:02d}" for index in range(1, 9))
_IMAGE_INPUTS = tuple(f"image_{index:02d}" for index in range(1, 11))
_MAX_CONTEXT_SLOTS = len(_CONTEXT_INPUTS)
_MAX_IMAGE_SLOTS = len(_IMAGE_INPUTS)
_DEFAULT_WORKFLOW_ID = "workflow_default"


def _list_workflow_skill_ids() -> list[str]:
    """把可用 Skill 暴露为 ComfyUI 下拉选项；无 Skill 时保留 none。"""
    result = ["none"]
    try:
        root = resolve_skill_root("")
        directories = sorted(path for path in root.iterdir() if path.is_dir())
    except OSError:
        return result
    for directory in directories:
        if (directory / "agent-contract.json").is_file():
            result.append(directory.name)
    return result


def _bounded_slot_count(value: int | None, maximum: int, default: int) -> int:
    try:
        count = int(value) if value is not None else default
    except (TypeError, ValueError):
        count = default
    return max(0, min(maximum, count))


def _attach_node_images(
    repository: WorkflowAgentRepository,
    workflow_id: str,
    agent_uid: str,
    image_values: tuple[object | None, ...],
) -> list:
    """把 Queue 节点的 IMAGE 输入落成当前 Session 内的 AssetRef。"""
    if not agent_uid or not any(value is not None for value in image_values):
        return []
    try:
        import numpy as np
        from PIL import Image
    except Exception as exc:
        raise RuntimeError("node image assets require Pillow and NumPy") from exc

    paths = repository.scope_paths(workflow_id, agent_uid, create=True)
    store = WorkflowAgentAssetStore(repository)
    refs = []
    with TemporaryDirectory(prefix="node-assets-", dir=str(paths.root)) as temporary:
        temporary_root = Path(temporary)
        for slot, value in enumerate(image_values, start=1):
            if value is None:
                continue
            if not hasattr(value, "detach"):
                raise ValueError(f"image_{slot:02d} must be a tensor")
            array = value.detach().cpu().numpy()
            batch_size = int(array.shape[0]) if array.ndim == 4 else 1
            if array.ndim == 4:
                array = array[0]
            if array.ndim != 3:
                raise ValueError(f"image_{slot:02d} must have HWC image shape")
            if array.shape[-1] == 1:
                array = np.repeat(array, 3, axis=-1)
            if array.shape[-1] not in (3, 4):
                raise ValueError(f"image_{slot:02d} must have 1, 3 or 4 channels")
            if np.issubdtype(array.dtype, np.floating):
                array = np.clip(array * 255.0, 0, 255)
            array = array.astype(np.uint8)
            source_path = temporary_root / f"image_{slot:02d}.png"
            Image.fromarray(array).save(source_path)
            refs.append(
                store.attach(
                    workflow_id,
                    agent_uid,
                    source_path,
                    asset_type="image",
                    created_by=agent_uid,
                    source="node_input",
                    metadata={"node_input": f"image_{slot:02d}", "batch_size": batch_size},
                )
            )
    return refs


class RyanWorkflowAgent:
    """固定 8 路 Context / 10 路 Image Socket 的通用 Agent 节点。"""

    @classmethod
    def INPUT_TYPES(cls):
        optional = {name: (RYAN_CONTEXT,) for name in _CONTEXT_INPUTS}
        optional.update({name: ("IMAGE",) for name in _IMAGE_INPUTS})
        skill_ids = _list_workflow_skill_ids()
        return {
            "required": {
                "skill_id": (
                    skill_ids,
                    {"default": "creative-story-planner" if "creative-story-planner" in skill_ids else skill_ids[0]},
                ),
                "agent_name": ("STRING", {"default": ""}),
                "context_slot_count": (
                    "INT",
                    {"default": 1, "min": 0, "max": _MAX_CONTEXT_SLOTS, "step": 1},
                ),
                "image_slot_count": (
                    "INT",
                    {"default": 1, "min": 0, "max": _MAX_IMAGE_SLOTS, "step": 1},
                ),
                "workflow_id": ("STRING", {"default": "", "hidden": True}),
                "agent_uid": ("STRING", {"default": "", "hidden": True}),
                # 旧 Workflow 可能把隐藏 widget 保存为空字符串；STRING 让 Queue 校验先通过，
                # 而 revision 只用于缓存键，不参与节点业务计算。
                "commit_revision": ("STRING", {"default": "0", "hidden": True}),
                "profile_path": ("STRING", {"default": "", "hidden": True}),
                "skill_root": ("STRING", {"default": "", "hidden": True}),
            },
            "optional": optional,
        }

    RETURN_TYPES = (
        RYAN_CONTEXT, "STRING", "STRING", "STRING", "STRING", "STRING", "STRING", "STRING",
        "STRING", "STRING", "STRING",
    )
    RETURN_NAMES = (
        "context", "response_text", "session_dir", "context_json",
        "artifact_text", "image_prompt", "storyboard_prompt", "video_prompt",
        "concept_image_prompt", "keyframe_prompt", "audio_prompt",
    )
    FUNCTION = "run"
    # Agent 节点可以作为 DAG 的终点；否则只有 Agent 链的 Workflow 会被 ComfyUI 判定为无输出。
    OUTPUT_NODE = True
    CATEGORY = "Ryan Utils / Agent"
    DESCRIPTION = "确定性合并上游 RYAN_CONTEXT 与当前 Agent 最新 Commit；不会启动 Pi 或 LLM。"

    @classmethod
    def IS_CHANGED(
        cls,
        workflow_id="",
        agent_uid="",
        commit_revision=0,
        context_slot_count=1,
        image_slot_count=1,
        **_kwargs,
    ):
        """Commit 文件变更也必须让 Queue 重新执行，避免仅 widget revision 未同步时读到空缓存。"""
        stamp = ""
        try:
            if workflow_id and agent_uid:
                path = (
                    WorkflowAgentRepository.from_output_root()
                    .scope_paths(str(workflow_id), str(agent_uid), create=False)
                    .latest_commit
                )
                if path.exists():
                    stat = path.stat()
                    stamp = f"{getattr(stat, 'st_mtime_ns', int(stat.st_mtime * 1_000_000_000))}:{stat.st_size}"
        except Exception:
            stamp = ""
        return (
            f"{workflow_id}:{agent_uid}:{commit_revision}:"
            f"{context_slot_count}:{image_slot_count}:{stamp}"
        )

    def run(
        self,
        skill_id="none",
        agent_name="",
        context_slot_count=1,
        image_slot_count=1,
        workflow_id="",
        agent_uid="",
        commit_revision=0,
        profile_path="",
        skill_root="",
        context_01=None,
        context_02=None,
        context_03=None,
        context_04=None,
        context_05=None,
        context_06=None,
        context_07=None,
        context_08=None,
        image_01=None,
        image_02=None,
        image_03=None,
        image_04=None,
        image_05=None,
        image_06=None,
        image_07=None,
        image_08=None,
        image_09=None,
        image_10=None,
    ):
        del skill_id, agent_name, profile_path, skill_root
        all_image_values = (
            image_01, image_02, image_03, image_04, image_05,
            image_06, image_07, image_08, image_09, image_10,
        )
        all_context_values = (
            context_01, context_02, context_03, context_04,
            context_05, context_06, context_07, context_08,
        )
        context_count = _bounded_slot_count(context_slot_count, _MAX_CONTEXT_SLOTS, 1)
        image_count = _bounded_slot_count(image_slot_count, _MAX_IMAGE_SLOTS, 1)
        context_values = all_context_values[:context_count]
        image_values = all_image_values[:image_count]
        resolved_workflow = validate_workflow_id(workflow_id) if workflow_id else None
        if resolved_workflow is None:
            for value in context_values:
                if isinstance(value, RyanContext):
                    resolved_workflow = value.workflow_id
                    break
                if isinstance(value, dict) and value.get("workflow_id"):
                    resolved_workflow = validate_workflow_id(value["workflow_id"])
                    break
        resolved_workflow = resolved_workflow or _DEFAULT_WORKFLOW_ID
        upstream = merge_contexts(context_values, workflow_id=resolved_workflow)

        commit = None
        session_dir = ""
        safe_agent_uid = ""
        node_assets = []
        if agent_uid:
            safe_agent_uid = validate_agent_uid(agent_uid)
            repository = WorkflowAgentRepository.from_output_root()
            commit = repository.read_latest_commit(resolved_workflow, safe_agent_uid)
            node_assets = _attach_node_images(
                repository, resolved_workflow, safe_agent_uid, image_values,
            )
            if commit:
                session_dir = str(repository.scope_paths(resolved_workflow, safe_agent_uid, create=False).root)
        output = append_commit(upstream, commit, workflow_id=resolved_workflow)
        if node_assets:
            output = merge_contexts(
                [output, RyanContext(workflow_id=resolved_workflow, assets=node_assets)],
                workflow_id=resolved_workflow,
            )
        response_text = ""
        if commit:
            entry = output.entries[-1] if output.entries else None
            if entry is not None:
                response_text = entry.content
            if not session_dir and safe_agent_uid:
                session_dir = str(
                    WorkflowAgentRepository.from_output_root()
                    .scope_paths(resolved_workflow, safe_agent_uid, create=False)
                    .root
                )
        artifact_text = ""
        image_prompt = ""
        storyboard_prompt = ""
        video_prompt = ""
        concept_image_prompt = ""
        keyframe_prompt = ""
        audio_prompt = ""
        if commit:
            commit_entry_id = str(commit.get("entry_id") or commit.get("entry", {}).get("entry_id") or "")
            committed_entry = next(
                (entry for entry in output.entries if entry.entry_id == commit_entry_id),
                None,
            )
            if committed_entry is not None:
                outputs = artifact_outputs(committed_entry)
                artifact_text = outputs[0].text if outputs else ""
                for item in outputs:
                    if not image_prompt and item.kind == "image_prompt":
                        image_prompt = item.text
                    if not concept_image_prompt and item.kind == "concept_image_prompt":
                        concept_image_prompt = item.text
                    if not storyboard_prompt and item.kind in {"storyboard_prompt", "storyboard_sheet_prompt", "shot_prompt"}:
                        storyboard_prompt = item.text
                    if not keyframe_prompt and item.kind == "keyframe_prompt":
                        keyframe_prompt = item.text
                    if not video_prompt and item.kind in {"video_prompt", "shot_video_prompt"}:
                        video_prompt = item.text
                    if not audio_prompt and item.kind == "audio_prompt":
                        audio_prompt = item.text
        context_json = output.to_json()
        return {
            # ComfyUI 不会把普通 STRING 输出自动显示在节点结果面板；
            # 同步 text UI 才能让用户在 Queue 后直接看到 Agent 的正式产物。
            "ui": {"context_json": [context_json], "text": [response_text]},
            "result": (
                output, response_text, session_dir, context_json,
                artifact_text, image_prompt, storyboard_prompt, video_prompt,
                concept_image_prompt, keyframe_prompt, audio_prompt,
            ),
        }


__all__ = ["RyanWorkflowAgent"]
