import json
from pathlib import Path

from ..acp.contracts import load_manifest, load_profile
from ..acp.file_exporter import (
    NODE_SLUG_IMAGE_ANALYZE,
    NODE_SLUG_IMAGE_PROMPT,
    NODE_SLUG_MINIMAX_H3_VIDEO_PROMPT,
    NODE_SLUG_VIDEO_PROMPT,
    export_prompt_to_file,
)
from ..acp.runtime import execute_text_session, map_result_fields
from ..acp.skill_resolver import resolve_skill_binding
from ..acp.workspace import prepare_workspace
from .comfy_image_inputs import (
    MAX_RYAN_IMAGE_SLOTS,
    build_image_slot_input_types,
    image_slot_name,
    resolve_image_inputs_for_acp,
    slots_from_explicit_args,
)


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROFILE_PATH = PACKAGE_ROOT / "acp" / "fixtures" / "profiles" / "local_pi.json"
DEFAULT_MANIFEST_PATH = PACKAGE_ROOT / "acp" / "fixtures" / "manifests" / "universal_agent.json"
DEFAULT_IMAGE_PROMPT_MANIFEST_PATH = (
    PACKAGE_ROOT / "acp" / "fixtures" / "manifests" / "image_prompt_agent.json"
)
DEFAULT_VIDEO_PROMPT_MANIFEST_PATH = (
    PACKAGE_ROOT / "acp" / "fixtures" / "manifests" / "video_prompt_agent.json"
)
DEFAULT_IMAGE_ANALYZE_MANIFEST_PATH = (
    PACKAGE_ROOT / "acp" / "fixtures" / "manifests" / "image_analyze_agent.json"
)
DEFAULT_MINIMAX_H3_VIDEO_PROMPT_MANIFEST_PATH = (
    PACKAGE_ROOT / "acp" / "fixtures" / "manifests" / "minimax_h3_video_prompt_agent.json"
)
DEFAULT_WORKSPACE_ROOT = "output/acp_workspace"

IMAGE_REVERSE_CATEGORIES = (
    "general",
    "typography_logo",
    "landscape",
    "photography",
    "illustration",
    "render_3d",
    "ip_character",
)
OUTPUT_LANGUAGE_OPTIONS = ("bilingual", "zh", "en")


def _require_image_paths_or_slots(image_paths: str, slots: list) -> None:
    if parse_multiline_paths(image_paths):
        return
    if any(s is not None for s in slots):
        return
    raise ValueError(
        "At least one image is required: connect image_01..image_N or provide image_paths"
    )


def _resolve_path(path_text: str) -> Path:
    path = Path(path_text).expanduser()
    if path.is_absolute() or path.exists():
        return path
    return Path.cwd() / path


def _resolve_workspace_root(node_value: str, profile: dict) -> Path:
    """节点非空优先；否则 profile.workspace_root；再否则默认相对路径。"""
    text = (node_value or "").strip()
    if text:
        return Path(text)
    profile_root = (profile.get("workspace_root") or "").strip()
    if profile_root:
        return Path(profile_root)
    return Path(DEFAULT_WORKSPACE_ROOT)


def parse_multiline_paths(paths_text: str) -> list[str]:
    if not paths_text or not str(paths_text).strip():
        return []
    return [line.strip() for line in str(paths_text).splitlines() if line.strip()]


def _format_optional_fields(**fields: str) -> str:
    lines = []
    for label, value in fields.items():
        text = (value or "").strip()
        if text:
            lines.append(f"{label}: {text}")
    if not lines:
        return ""
    return "\n".join(lines) + "\n"


def _serialize_raw_result(mapped: dict) -> str:
    raw_result_value = mapped.get("raw_result_json", "")
    if isinstance(raw_result_value, dict):
        return json.dumps(raw_result_value, ensure_ascii=False)
    return str(raw_result_value)


def _maybe_export_prompt(
    *,
    export_to_file: bool,
    response_text: str,
    node_name: str,
    node_slug: str,
    session_id: str,
    export_filename: str = "",
    category: str = "",
) -> None:
    if not export_to_file:
        return
    export_prompt_to_file(
        response_text=response_text,
        node_name=node_name,
        node_slug=node_slug,
        session_id=session_id,
        export_filename=export_filename,
        category=category,
    )


def _collect_run_image_slots(image_slot_count=1, **image_kwargs):
    """从 run() 的 image_01..image_10 参数收集槽位，避免四节点复制 10 个形参组装。"""
    slot_values = {}
    for i in range(1, MAX_RYAN_IMAGE_SLOTS + 1):
        name = image_slot_name(i)
        if name in image_kwargs:
            slot_values[name] = image_kwargs[name]
    return slots_from_explicit_args(image_slot_count, **slot_values)


def run_fixed_acp_agent(
    *,
    manifest_path: str,
    profile_path: str,
    workspace_root: str,
    session_id: str,
    skill_root: str,
    user_text: str,
    image_paths: str = "",
    file_paths: str = "",
    extra_user_lines: str = "",
    image_slots: list | None = None,
) -> tuple[str, str, str]:
    manifest = load_manifest(_resolve_path(manifest_path))
    profile = load_profile(_resolve_path(profile_path))
    binding = resolve_skill_binding(
        manifest,
        skill_root,
        user_skill_id="",
        allow_user_skill=False,
    )

    merged_text = (user_text or "").strip()
    if extra_user_lines.strip():
        merged_text = f"{merged_text}\n\n{extra_user_lines.strip()}".strip()

    workspace = _resolve_workspace_root(workspace_root, profile)
    # 先准备 session，槽位可直接写入 session/input/images，避免额外 staging
    session_dir = prepare_workspace(workspace, session_id)
    image_inputs = resolve_image_inputs_for_acp(
        session_dir=session_dir,
        image_paths_text=image_paths,
        image_slots=image_slots or [],
        parse_paths=parse_multiline_paths,
    )

    result = execute_text_session(
        workspace_root=workspace,
        session_id=session_id,
        skill_root=binding.skill_root,
        skill_id=binding.skill_id,
        context_template=manifest["context_template"],
        user_text=merged_text,
        runner_profile=profile,
        image_inputs=image_inputs,
        file_inputs=parse_multiline_paths(file_paths),
    )
    mapped = map_result_fields(result, manifest["result_mapping"])
    return (
        str(mapped.get("response_text", "")),
        result["session_dir"],
        _serialize_raw_result(mapped),
    )


def _list_skills() -> list[str]:
    skills_dir = PACKAGE_ROOT / "acp" / "fixtures" / "skills"
    base = ["none"]
    if not skills_dir.exists() or not skills_dir.is_dir():
        return base
    skills = sorted([p.name for p in skills_dir.iterdir() if p.is_dir()])
    return base + skills


class RyanACPUniversalAgent:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "skill_id": (_list_skills(),),
                "user_text": ("STRING", {"default": "", "multiline": True}),
            },
            "optional": build_image_slot_input_types(include_paths=False),
        }

    RETURN_TYPES = ("STRING", "STRING", "STRING")
    RETURN_NAMES = ("response_text", "session_dir", "raw_result_json")
    FUNCTION = "run"
    CATEGORY = "Ryan Utils / ACP"

    def run(
        self,
        skill_id,
        user_text,
        image_slot_count=2,
        profile_path=str(DEFAULT_PROFILE_PATH),
        manifest_path=str(DEFAULT_MANIFEST_PATH),
        workspace_root=DEFAULT_WORKSPACE_ROOT,
        session_id="session_manual",
        skill_root="",
        **image_kwargs,
    ):
        manifest = load_manifest(_resolve_path(manifest_path))
        profile = load_profile(_resolve_path(profile_path))
        binding = resolve_skill_binding(
            manifest,
            skill_root,
            user_skill_id=skill_id,
            allow_user_skill=True,
        )
        slots = _collect_run_image_slots(image_slot_count, **image_kwargs)
        workspace = _resolve_workspace_root(workspace_root, profile)
        session_dir = prepare_workspace(workspace, session_id)
        image_inputs = resolve_image_inputs_for_acp(
            session_dir=session_dir,
            image_paths_text="",
            image_slots=slots,
            parse_paths=parse_multiline_paths,
        )
        result = execute_text_session(
            workspace_root=workspace,
            session_id=session_id,
            skill_root=binding.skill_root,
            skill_id=binding.skill_id,
            context_template=manifest["context_template"],
            user_text=user_text,
            runner_profile=profile,
            image_inputs=image_inputs,
        )
        mapped = map_result_fields(result, manifest["result_mapping"])
        return (
            str(mapped.get("response_text", "")),
            result["session_dir"],
            _serialize_raw_result(mapped),
        )


class RyanACPImagePromptAgent:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "user_text": ("STRING", {"default": "", "multiline": True}),
                "export_to_file": ("BOOLEAN", {"default": False}),
            },
            "optional": {
                **build_image_slot_input_types(include_paths=False),
                "export_filename": ("STRING", {"default": ""}),
            },
        }

    RETURN_TYPES = ("STRING", "STRING", "STRING")
    RETURN_NAMES = ("response_text", "session_dir", "raw_result_json")
    FUNCTION = "run"
    CATEGORY = "Ryan Utils / ACP"

    def run(
        self,
        user_text,
        export_to_file,
        image_slot_count=2,
        export_filename="",
        profile_path=str(DEFAULT_PROFILE_PATH),
        workspace_root=DEFAULT_WORKSPACE_ROOT,
        session_id="session_image_prompt",
        skill_root="",
        manifest_path=str(DEFAULT_IMAGE_PROMPT_MANIFEST_PATH),
        **image_kwargs,
    ):
        slots = _collect_run_image_slots(image_slot_count, **image_kwargs)
        response_text, session_dir, raw_json = run_fixed_acp_agent(
            manifest_path=manifest_path,
            profile_path=profile_path,
            workspace_root=workspace_root,
            session_id=session_id,
            skill_root=skill_root,
            user_text=user_text,
            image_paths="",
            extra_user_lines="",
            image_slots=slots,
        )
        _maybe_export_prompt(
            export_to_file=export_to_file,
            response_text=response_text,
            node_name="Ryan Image Prompt Agent",
            node_slug=NODE_SLUG_IMAGE_PROMPT,
            session_id=session_id,
            export_filename=export_filename,
        )
        return response_text, session_dir, raw_json


class RyanACPVideoPromptAgent:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "user_text": ("STRING", {"default": "", "multiline": True}),
                "export_to_file": ("BOOLEAN", {"default": False}),
            },
            "optional": {
                **build_image_slot_input_types(include_paths=False),
                "export_filename": ("STRING", {"default": ""}),
            },
        }

    RETURN_TYPES = ("STRING", "STRING", "STRING")
    RETURN_NAMES = ("response_text", "session_dir", "raw_result_json")
    FUNCTION = "run"
    CATEGORY = "Ryan Utils / ACP"

    def run(
        self,
        user_text,
        export_to_file,
        image_slot_count=2,
        export_filename="",
        profile_path=str(DEFAULT_PROFILE_PATH),
        workspace_root=DEFAULT_WORKSPACE_ROOT,
        session_id="session_video_prompt",
        skill_root="",
        manifest_path=str(DEFAULT_VIDEO_PROMPT_MANIFEST_PATH),
        **image_kwargs,
    ):
        slots = _collect_run_image_slots(image_slot_count, **image_kwargs)
        response_text, session_dir, raw_json = run_fixed_acp_agent(
            manifest_path=manifest_path,
            profile_path=profile_path,
            workspace_root=workspace_root,
            session_id=session_id,
            skill_root=skill_root,
            user_text=user_text,
            image_paths="",
            extra_user_lines="",
            image_slots=slots,
        )
        _maybe_export_prompt(
            export_to_file=export_to_file,
            response_text=response_text,
            node_name="Ryan Video Prompt Agent",
            node_slug=NODE_SLUG_VIDEO_PROMPT,
            session_id=session_id,
            export_filename=export_filename,
        )
        return response_text, session_dir, raw_json


class RyanACPImageAnalyzeAgent:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "user_text": ("STRING", {"default": "", "multiline": True}),
                "category": (list(IMAGE_REVERSE_CATEGORIES), {"default": "general"}),
                "output_language": (list(OUTPUT_LANGUAGE_OPTIONS), {"default": "bilingual"}),
                "export_to_file": ("BOOLEAN", {"default": False}),
            },
            "optional": {
                **build_image_slot_input_types(include_paths=False),
                "export_filename": ("STRING", {"default": ""}),
            },
        }

    RETURN_TYPES = ("STRING", "STRING", "STRING")
    RETURN_NAMES = ("response_text", "session_dir", "raw_result_json")
    FUNCTION = "run"
    CATEGORY = "Ryan Utils / ACP"

    def run(
        self,
        user_text,
        category,
        output_language,
        export_to_file,
        image_slot_count=2,
        export_filename="",
        profile_path=str(DEFAULT_PROFILE_PATH),
        workspace_root=DEFAULT_WORKSPACE_ROOT,
        session_id="session_image_analyze",
        skill_root="",
        manifest_path=str(DEFAULT_IMAGE_ANALYZE_MANIFEST_PATH),
        **image_kwargs,
    ):
        slots = _collect_run_image_slots(image_slot_count, **image_kwargs)
        _require_image_paths_or_slots("", slots)
        extra = _format_optional_fields(
            category=category,
            output_language=output_language,
        )
        response_text, session_dir, raw_json = run_fixed_acp_agent(
            manifest_path=manifest_path,
            profile_path=profile_path,
            workspace_root=workspace_root,
            session_id=session_id,
            skill_root=skill_root,
            user_text=user_text,
            image_paths="",
            extra_user_lines=extra,
            image_slots=slots,
        )
        if export_to_file:
            _maybe_export_prompt(
                export_to_file=True,
                response_text=response_text,
                node_name="Ryan Image Analyze Agent",
                node_slug=NODE_SLUG_IMAGE_ANALYZE,
                session_id=session_id,
                export_filename=export_filename,
                category=category,
            )
        return response_text, session_dir, raw_json


H3_GENERATION_MODES = (
    "纯文生",
    "普通图生",
    "首帧生成",
    "首尾帧",
    "尾帧生成",
    "全能参考",
    "视频编辑",
    "视频续接",
)

H3_MODE_MAP = {
    "纯文生": "T2VA",
    "普通图生": "Ref2VA",
    "首帧生成": "I2VA",
    "首尾帧": "FL2VA",
    "尾帧生成": "L2VA",
    "全能参考": "Ref2VA",
    "视频编辑": "Ref2VA",
    "视频续接": "Ref2VA",
}

H3_TASK_RELATIONS = (
    "无",
    "Video Editing（视频编辑）",
    "Video Continuation（视频续接）",
    "Audio Reuse（音频复用）",
    "Audio Reference（音频参考）",
)


def _build_h3_extra_lines(
    generation_mode: str,
    task_relation: str,
    connected_image_count: int,
    video_paths: list[str],
    audio_paths: list[str],
    image_role_mapping: str = "",
    asset_role_mapping: str = "",
    video_sample_info: list[str] | None = None,
) -> str:
    """构建传给 Skill 的确定性模式、关系和素材上下文。"""
    lines: list[str] = [
        f"基础生成模式: {H3_MODE_MAP.get(generation_mode, generation_mode)}",
        f"用户界面模式: {generation_mode}",
        f"附加任务关系: {task_relation or '无'}",
    ]

    assets: list[str] = []
    if connected_image_count > 0:
        assets.append(f"图片: {connected_image_count} 张（已通过图片槽位上传）")
    if video_sample_info:
        assets.extend(video_sample_info)
    elif video_paths:
        assets.extend(f"视频{i}: {path}" for i, path in enumerate(video_paths, 1))
    if audio_paths:
        assets.extend(f"音频{i}: {path}" for i, path in enumerate(audio_paths, 1))

    lines.append("素材清单:")
    if assets:
        lines.extend(f"- {asset}" for asset in assets)
    else:
        lines.append("- 无（纯文本生成场景）")

    if image_role_mapping.strip():
        lines.extend(("图片角色映射:", image_role_mapping.strip()))
    if asset_role_mapping.strip():
        lines.extend(("素材角色映射:", asset_role_mapping.strip()))

    return "\n".join(lines) + "\n"

MAX_H3_IMAGE_SLOTS = 9
MAX_H3_VIDEO_SLOTS = 3
MAX_H3_AUDIO_SLOTS = 3


def build_h3_input_types() -> dict[str, tuple]:
    optional: dict[str, tuple] = {}
    # 保持旧字段顺序；ComfyUI 会按 widget 位置恢复已保存工作流。
    for i in range(1, MAX_H3_IMAGE_SLOTS + 1):
        optional[f"image_{i:02d}"] = ("IMAGE",)
    optional["image_slot_count"] = (
        "INT",
        {"default": 2, "min": 0, "max": MAX_H3_IMAGE_SLOTS, "step": 1},
    )

    for i in range(1, MAX_H3_VIDEO_SLOTS + 1):
        optional[f"video_{i:02d}"] = ("*",)
    optional["video_slot_count"] = (
        "INT",
        {"default": 1, "min": 0, "max": MAX_H3_VIDEO_SLOTS, "step": 1},
    )
    optional["video_start_frame"] = ("INT", {"default": 0, "min": 0, "max": 100000, "step": 1})
    optional["video_frame_count"] = ("INT", {"default": 0, "min": 0, "max": 100, "step": 1})

    for i in range(1, MAX_H3_AUDIO_SLOTS + 1):
        optional[f"audio_{i:02d}"] = ("*",)
    optional["audio_slot_count"] = (
        "INT",
        {"default": 0, "min": 0, "max": MAX_H3_AUDIO_SLOTS, "step": 1},
    )

    optional["export_filename"] = ("STRING", {"default": ""})
    # 新字段只能追加，不能插入旧字段中间。
    optional["task_relation"] = (list(H3_TASK_RELATIONS), {"default": "无"})
    optional["image_role_mapping"] = ("STRING", {"default": "", "multiline": True})
    optional["asset_role_mapping"] = ("STRING", {"default": "", "multiline": True})
    return optional


class RyanACPMiniMaxH3VideoPromptAgent:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "generation_mode": (list(H3_GENERATION_MODES), {"default": H3_GENERATION_MODES[0]}),
                "user_text": ("STRING", {"default": "", "multiline": True}),
                "export_to_file": ("BOOLEAN", {"default": False}),
            },
            "optional": build_h3_input_types(),
        }

    RETURN_TYPES = ("STRING", "STRING", "STRING")
    RETURN_NAMES = ("response_text", "session_dir", "raw_result_json")
    FUNCTION = "run"
    CATEGORY = "Ryan Utils / ACP"
    DESCRIPTION = (
        "MiniMax H3 视频提示词生成 ACP 智能体。"
        "支持 T2VA、I2VA、FL2VA、L2VA、Ref2VA，以及视频编辑、视频续接和音频复用/参考，"
        "支持动态控制图片插槽(0~9)、视频插槽(0~3)、音频插槽(0~3)，兼容 LoadVideo、LoadAudio 连线。"
        "可指定视频抽帧范围、图片角色映射和素材角色映射，生成符合官方 H3 结构的提示词。"
    )

    def run(
        self,
        generation_mode,
        user_text,
        export_to_file,
        task_relation="无",
        image_role_mapping="",
        asset_role_mapping="",
        image_slot_count=2,
        video_slot_count=1,
        video_start_frame=0,
        video_frame_count=0,
        audio_slot_count=0,
        export_filename="",
        profile_path=str(DEFAULT_PROFILE_PATH),
        workspace_root=DEFAULT_WORKSPACE_ROOT,
        session_id="session_minimax_h3_video_prompt",
        skill_root="",
        manifest_path=str(DEFAULT_MINIMAX_H3_VIDEO_PROMPT_MANIFEST_PATH),
        **kwargs,
    ):
        img_limit = max(0, min(int(image_slot_count if image_slot_count is not None else 2), MAX_H3_IMAGE_SLOTS))
        slots = [kwargs.get(f"image_{i:02d}") for i in range(1, img_limit + 1)] if img_limit > 0 else []
        connected_count = sum(1 for s in slots if s is not None)

        raw_video_inputs = []
        vid_limit = max(0, min(int(video_slot_count if video_slot_count is not None else 1), MAX_H3_VIDEO_SLOTS))
        for i in range(1, vid_limit + 1):
            val = kwargs.get(f"video_{i:02d}")
            if val is not None and val != "":
                raw_video_inputs.append((i, val))
        has_video_input = bool(raw_video_inputs)
        if not has_video_input:
            # 没有视频时，帧范围参数没有语义；忽略其旧工作流残值，
            # 避免前端恢复值或手动填写值触发无关校验。
            video_start_frame = 0
            video_frame_count = 0

        raw_audio_inputs = []
        aud_limit = max(0, min(int(audio_slot_count if audio_slot_count is not None else 0), MAX_H3_AUDIO_SLOTS))
        for i in range(1, aud_limit + 1):
            val = kwargs.get(f"audio_{i:02d}")
            if val is not None and val != "":
                raw_audio_inputs.append((i, val))

        # 视频抽帧处理与素材解析
        video_sample_info: list[str] = []
        sampled_image_paths: list[str] = []
        parsed_video_paths: list[str] = []
        profile = load_profile(_resolve_path(profile_path))
        workspace = _resolve_workspace_root(workspace_root, profile)
        session_dir_path = prepare_workspace(workspace, session_id)

        from ..acp.image_slot_paths import session_input_images_dir
        from ..core.video_utils import load_video_frames
        import numpy as np
        import torch
        from PIL import Image

        target_images_dir = session_input_images_dir(session_dir_path)
        target_images_dir.mkdir(parents=True, exist_ok=True)

        for v_idx, val in raw_video_inputs:
            # 仅对第一个视频源 (video_01, v_idx == 1) 应用 video_start_frame 和 video_frame_count 抽帧控制
            if v_idx == 1:
                cur_start_f = max(0, int(video_start_frame or 0))
                cur_count_f = max(1, int(video_frame_count or 1)) if int(video_frame_count or 0) > 0 else 0
            else:
                cur_start_f = 0
                cur_count_f = 0

            # 1. 若接入的是 IMAGE Tensor (例如 LoadVideo 解码出的视频帧)
            if isinstance(val, torch.Tensor):
                if val.ndim == 3:
                    val = val.unsqueeze(0)
                total_f = val.shape[0]
                slice_start = min(cur_start_f, max(0, total_f - 1))
                slice_end = min(total_f, slice_start + cur_count_f) if cur_count_f > 0 else total_f
                sub_tensor = val[slice_start:slice_end]

                video_sample_info.append(
                    f"视频{v_idx}: [IMAGE 视频帧批次]（共 {total_f} 帧，截取第 {slice_start}~{slice_end - 1} 帧共 {len(sub_tensor)} 帧供视觉分析）"
                )
                for f_i, frame_tensor in enumerate(sub_tensor):
                    arr = (frame_tensor.cpu().numpy() * 255.0).clip(0, 255).astype(np.uint8)
                    pil_img = Image.fromarray(arr)
                    frame_filename = f"video{v_idx:02d}_frame_{slice_start + f_i:04d}.png"
                    out_p = target_images_dir / frame_filename
                    sampled_image_paths.append(str(out_p))
                    pil_img.save(out_p, format="PNG")
                parsed_video_paths.append(f"video_slot_{v_idx:02d}_tensor_frames")

            # 2. 若接入的是路径字符串
            elif isinstance(val, str) and val.strip():
                vp = val.strip()
                parsed_video_paths.append(vp)
                if cur_count_f > 0:
                    try:
                        tensor_frames, loaded_count = load_video_frames(
                            vp,
                            skip_first_frames=cur_start_f,
                            frame_load_cap=cur_count_f,
                        )
                        end_f = cur_start_f + loaded_count - 1
                        video_sample_info.append(
                            f"视频{v_idx}: {vp}（已截取第 {cur_start_f}~{end_f} 帧共 {loaded_count} 帧画面作为视觉分析参考）"
                        )
                        for f_i, frame_tensor in enumerate(tensor_frames):
                            arr = (frame_tensor.cpu().numpy() * 255.0).clip(0, 255).astype(np.uint8)
                            pil_img = Image.fromarray(arr)
                            frame_filename = f"video{v_idx:02d}_frame_{cur_start_f + f_i:04d}.png"
                            out_p = target_images_dir / frame_filename
                            sampled_image_paths.append(str(out_p))
                            pil_img.save(out_p, format="PNG")
                    except Exception as exc:
                        print(f"⚠️ Video frame sampling failed for {vp}: {exc}")
                        video_sample_info.append(f"视频{v_idx}: {vp}")
                else:
                    video_sample_info.append(f"视频{v_idx}: {vp}")

            # 3. 其他对象类型 (如 VHS 节点字典等)
            elif isinstance(val, (dict, list, tuple)):
                p_str = str(val)
                parsed_video_paths.append(p_str)
                video_sample_info.append(f"视频{v_idx}: {p_str}")

        # 音频素材解析
        parsed_audio_paths = []
        for a_idx, val in raw_audio_inputs:
            if isinstance(val, str) and val.strip():
                parsed_audio_paths.append(val.strip())
            elif isinstance(val, dict):
                # 支持包含 filename 或 path 的音频字典
                apath = val.get("path") or val.get("filename") or str(val)
                parsed_audio_paths.append(str(apath))
            elif val is not None:
                parsed_audio_paths.append(str(val))

        extra = _build_h3_extra_lines(
            generation_mode=generation_mode,
            task_relation=task_relation,
            connected_image_count=connected_count,
            video_paths=parsed_video_paths,
            audio_paths=parsed_audio_paths,
            image_role_mapping=image_role_mapping,
            asset_role_mapping=asset_role_mapping,
            video_sample_info=video_sample_info if video_sample_info else None,
        )

        # 图片槽位由 resolver 处理；视频抽帧图片已在当前 session/input/images 下，
        # 通过 image_paths 传入后会被识别为 session 内路径，不会重复复制。
        acp_image_paths = "\n".join(sampled_image_paths)
        acp_file_paths = "\n".join(
            path
            for path in (*parsed_video_paths, *parsed_audio_paths)
            if Path(path).expanduser().exists()
        )

        response_text, session_dir, raw_json = run_fixed_acp_agent(
            manifest_path=manifest_path,
            profile_path=profile_path,
            workspace_root=workspace_root,
            session_id=session_id,
            skill_root=skill_root,
            user_text=user_text,
            image_paths=acp_image_paths,
            file_paths=acp_file_paths,
            extra_user_lines=extra,
            image_slots=slots,
        )
        _maybe_export_prompt(
            export_to_file=export_to_file,
            response_text=response_text,
            node_name="Ryan MiniMax H3 Video Prompt Agent",
            node_slug=NODE_SLUG_MINIMAX_H3_VIDEO_PROMPT,
            session_id=session_id,
            export_filename=export_filename,
        )
        return response_text, session_dir, raw_json



