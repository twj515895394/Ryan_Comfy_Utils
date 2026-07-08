import json
from pathlib import Path

from ..acp.contracts import load_manifest, load_profile
from ..acp.runtime import execute_text_session, map_result_fields


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROFILE_PATH = PACKAGE_ROOT / "acp" / "fixtures" / "profiles" / "local_codex.json"
DEFAULT_MANIFEST_PATH = PACKAGE_ROOT / "acp" / "fixtures" / "manifests" / "universal_agent.json"


def _resolve_path(path_text: str) -> Path:
    path = Path(path_text).expanduser()
    if path.is_absolute() or path.exists():
        return path
    return Path.cwd() / path


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
            }
        }

    RETURN_TYPES = ("STRING", "STRING", "STRING")
    RETURN_NAMES = ("response_text", "session_dir", "raw_result_json")
    FUNCTION = "run"
    CATEGORY = "Ryan Utils / ACP"

    def run(self, skill_id, user_text, profile_path, manifest_path, workspace_root, session_id, skill_root):
        manifest = load_manifest(_resolve_path(manifest_path))
        profile = load_profile(_resolve_path(profile_path))
        result = execute_text_session(
            workspace_root=Path(workspace_root),
            session_id=session_id,
            skill_root=Path(skill_root).expanduser(),
            skill_id=skill_id or manifest["skill_id"],
            context_template=manifest["context_template"],
            user_text=user_text,
            runner_profile=profile,
        )
        mapped = map_result_fields(result, manifest["result_mapping"])
        raw_result_value = mapped.get("raw_result_json", "")
        if isinstance(raw_result_value, dict):
            raw_result_text = json.dumps(raw_result_value, ensure_ascii=False)
        else:
            raw_result_text = str(raw_result_value)
        return (
            str(mapped.get("response_text", "")),
            result["session_dir"],
            raw_result_text,
        )
