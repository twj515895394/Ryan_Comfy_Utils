import json
from pathlib import Path

from ..acp.contracts import load_manifest, load_profile
from ..acp.file_exporter import (
    NODE_SLUG_IMAGE_ANALYZE,
    NODE_SLUG_IMAGE_PROMPT,
    NODE_SLUG_VIDEO_PROMPT,
    export_prompt_to_file,
)
from ..acp.runtime import execute_text_session, map_result_fields
from ..acp.skill_loader import resolve_skill_root
from .comfy_image_inputs import (
    build_image_slot_input_types,
    resolve_image_inputs_for_acp,
    slots_from_explicit_args,
)


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROFILE_PATH = PACKAGE_ROOT / "acp" / "fixtures" / "profiles" / "local_codex.json"
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
    skill_id = manifest["skill_id"]
    if not skill_id:
        raise ValueError("Fixed manifest must define skill_id")

    merged_text = (user_text or "").strip()
    if extra_user_lines.strip():
        merged_text = f"{merged_text}\n\n{extra_user_lines.strip()}".strip()

    image_inputs = resolve_image_inputs_for_acp(
        workspace_root=Path(workspace_root),
        session_id=session_id,
        image_paths_text=image_paths,
        image_slots=image_slots or [],
        parse_paths=parse_multiline_paths,
    )

    result = execute_text_session(
        workspace_root=Path(workspace_root),
        session_id=session_id,
        skill_root=resolve_skill_root(skill_root),
        skill_id=skill_id,
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


class RyanACPUniversalAgent:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "skill_id": ("STRING", {"default": ""}),
                "user_text": ("STRING", {"default": "", "multiline": True}),
                "profile_path": ("STRING", {"default": str(DEFAULT_PROFILE_PATH)}),
                "manifest_path": ("STRING", {"default": str(DEFAULT_MANIFEST_PATH)}),
                "workspace_root": ("STRING", {"default": "output/acp_workspace"}),
                "session_id": ("STRING", {"default": "session_manual"}),
                "skill_root": ("STRING", {"default": ""}),
            },
            "optional": build_image_slot_input_types(include_paths=True),
        }

    RETURN_TYPES = ("STRING", "STRING", "STRING")
    RETURN_NAMES = ("response_text", "session_dir", "raw_result_json")
    FUNCTION = "run"
    CATEGORY = "Ryan Utils / ACP"

    def run(
        self,
        skill_id,
        user_text,
        profile_path,
        manifest_path,
        workspace_root,
        session_id,
        skill_root,
        image_slot_count=1,
        image_paths="",
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
        manifest = load_manifest(_resolve_path(manifest_path))
        profile = load_profile(_resolve_path(profile_path))
        slots = slots_from_explicit_args(
            image_slot_count,
            image_01=image_01,
            image_02=image_02,
            image_03=image_03,
            image_04=image_04,
            image_05=image_05,
            image_06=image_06,
            image_07=image_07,
            image_08=image_08,
            image_09=image_09,
            image_10=image_10,
        )
        image_inputs = resolve_image_inputs_for_acp(
            workspace_root=Path(workspace_root),
            session_id=session_id,
            image_paths_text=image_paths,
            image_slots=slots,
            parse_paths=parse_multiline_paths,
        )
        result = execute_text_session(
            workspace_root=Path(workspace_root),
            session_id=session_id,
            skill_root=resolve_skill_root(skill_root),
            skill_id=skill_id or manifest["skill_id"],
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
                "profile_path": ("STRING", {"default": str(DEFAULT_PROFILE_PATH)}),
                "workspace_root": ("STRING", {"default": "output/acp_workspace"}),
                "session_id": ("STRING", {"default": "session_image_prompt"}),
                "export_to_file": ("BOOLEAN", {"default": False}),
            },
            "optional": {
                **build_image_slot_input_types(include_paths=True),
                "style": ("STRING", {"default": ""}),
                "subject": ("STRING", {"default": ""}),
                "scene": ("STRING", {"default": ""}),
                "extra_prompt": ("STRING", {"default": "", "multiline": True}),
                "export_filename": ("STRING", {"default": ""}),
                "skill_root": ("STRING", {"default": ""}),
                "manifest_path": ("STRING", {"default": str(DEFAULT_IMAGE_PROMPT_MANIFEST_PATH)}),
            },
        }

    RETURN_TYPES = ("STRING", "STRING", "STRING")
    RETURN_NAMES = ("response_text", "session_dir", "raw_result_json")
    FUNCTION = "run"
    CATEGORY = "Ryan Utils / ACP"

    def run(
        self,
        user_text,
        profile_path,
        workspace_root,
        session_id,
        export_to_file,
        image_slot_count=1,
        image_paths="",
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
        style="",
        subject="",
        scene="",
        extra_prompt="",
        export_filename="",
        skill_root="",
        manifest_path=str(DEFAULT_IMAGE_PROMPT_MANIFEST_PATH),
    ):
        extra = _format_optional_fields(
            style=style,
            subject=subject,
            scene=scene,
            extra_prompt=extra_prompt,
        )
        slots = slots_from_explicit_args(
            image_slot_count,
            image_01=image_01,
            image_02=image_02,
            image_03=image_03,
            image_04=image_04,
            image_05=image_05,
            image_06=image_06,
            image_07=image_07,
            image_08=image_08,
            image_09=image_09,
            image_10=image_10,
        )
        response_text, session_dir, raw_json = run_fixed_acp_agent(
            manifest_path=manifest_path,
            profile_path=profile_path,
            workspace_root=workspace_root,
            session_id=session_id,
            skill_root=skill_root,
            user_text=user_text,
            image_paths=image_paths,
            extra_user_lines=extra,
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
                "profile_path": ("STRING", {"default": str(DEFAULT_PROFILE_PATH)}),
                "workspace_root": ("STRING", {"default": "output/acp_workspace"}),
                "session_id": ("STRING", {"default": "session_video_prompt"}),
                "export_to_file": ("BOOLEAN", {"default": False}),
            },
            "optional": {
                **build_image_slot_input_types(include_paths=True),
                "task": ("STRING", {"default": "", "multiline": True}),
                "extra_prompt": ("STRING", {"default": "", "multiline": True}),
                "export_filename": ("STRING", {"default": ""}),
                "skill_root": ("STRING", {"default": ""}),
                "manifest_path": ("STRING", {"default": str(DEFAULT_VIDEO_PROMPT_MANIFEST_PATH)}),
            },
        }

    RETURN_TYPES = ("STRING", "STRING", "STRING")
    RETURN_NAMES = ("response_text", "session_dir", "raw_result_json")
    FUNCTION = "run"
    CATEGORY = "Ryan Utils / ACP"

    def run(
        self,
        user_text,
        profile_path,
        workspace_root,
        session_id,
        export_to_file,
        image_slot_count=1,
        image_paths="",
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
        task="",
        extra_prompt="",
        export_filename="",
        skill_root="",
        manifest_path=str(DEFAULT_VIDEO_PROMPT_MANIFEST_PATH),
    ):
        extra = _format_optional_fields(task=task, extra_prompt=extra_prompt)
        slots = slots_from_explicit_args(
            image_slot_count,
            image_01=image_01,
            image_02=image_02,
            image_03=image_03,
            image_04=image_04,
            image_05=image_05,
            image_06=image_06,
            image_07=image_07,
            image_08=image_08,
            image_09=image_09,
            image_10=image_10,
        )
        response_text, session_dir, raw_json = run_fixed_acp_agent(
            manifest_path=manifest_path,
            profile_path=profile_path,
            workspace_root=workspace_root,
            session_id=session_id,
            skill_root=skill_root,
            user_text=user_text,
            image_paths=image_paths,
            extra_user_lines=extra,
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
                "profile_path": ("STRING", {"default": str(DEFAULT_PROFILE_PATH)}),
                "workspace_root": ("STRING", {"default": "output/acp_workspace"}),
                "session_id": ("STRING", {"default": "session_image_analyze"}),
                "export_to_file": ("BOOLEAN", {"default": False}),
            },
            "optional": {
                **build_image_slot_input_types(include_paths=True),
                "extra_prompt": ("STRING", {"default": "", "multiline": True}),
                "export_filename": ("STRING", {"default": ""}),
                "skill_root": ("STRING", {"default": ""}),
                "manifest_path": ("STRING", {"default": str(DEFAULT_IMAGE_ANALYZE_MANIFEST_PATH)}),
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
        profile_path,
        workspace_root,
        session_id,
        export_to_file,
        image_slot_count=1,
        image_paths="",
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
        extra_prompt="",
        export_filename="",
        skill_root="",
        manifest_path=str(DEFAULT_IMAGE_ANALYZE_MANIFEST_PATH),
    ):
        slots = slots_from_explicit_args(
            image_slot_count,
            image_01=image_01,
            image_02=image_02,
            image_03=image_03,
            image_04=image_04,
            image_05=image_05,
            image_06=image_06,
            image_07=image_07,
            image_08=image_08,
            image_09=image_09,
            image_10=image_10,
        )
        _require_image_paths_or_slots(image_paths, slots)
        extra = _format_optional_fields(
            category=category,
            output_language=output_language,
            extra_prompt=extra_prompt,
        )
        response_text, session_dir, raw_json = run_fixed_acp_agent(
            manifest_path=manifest_path,
            profile_path=profile_path,
            workspace_root=workspace_root,
            session_id=session_id,
            skill_root=skill_root,
            user_text=user_text,
            image_paths=image_paths,
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