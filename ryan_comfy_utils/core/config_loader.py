import json
import os
from pathlib import Path

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG_DIR = PACKAGE_ROOT / "config"
PRIVATE_PROFILE_PATH = DEFAULT_CONFIG_DIR / "llm_profiles.json"
EXAMPLE_PROFILE_PATH = DEFAULT_CONFIG_DIR / "llm_profiles.example.json"
ENV_PROFILE_PATH = "RYAN_COMFY_UTILS_PROFILE_PATH"


def get_profile_config_path() -> Path:
    env_path = os.environ.get(ENV_PROFILE_PATH)
    if env_path:
        path = Path(env_path).expanduser()
        if path.exists():
            return path
        raise FileNotFoundError(f"RYAN_COMFY_UTILS_PROFILE_PATH not found: {path}")

    if PRIVATE_PROFILE_PATH.exists():
        return PRIVATE_PROFILE_PATH

    if EXAMPLE_PROFILE_PATH.exists():
        return EXAMPLE_PROFILE_PATH

    raise FileNotFoundError("No llm_profiles config found.")


def load_profiles() -> dict:
    path = get_profile_config_path()
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if "profiles" not in data or not isinstance(data["profiles"], dict):
        raise ValueError(f"Invalid llm profile config: missing profiles in {path}")

    return data


def list_profile_names():
    data = load_profiles()
    names = sorted(data.get("profiles", {}).keys())
    if not names:
        return ["default"]
    return names


def resolve_profile(profile_name: str | None = None, model_override: str | None = None) -> dict:
    data = load_profiles()
    profiles = data["profiles"]
    default_name = data.get("default") or next(iter(profiles.keys()))
    selected = profile_name or default_name

    if selected not in profiles:
        raise ValueError(f"Profile not found: {selected}. Available: {', '.join(sorted(profiles.keys()))}")

    profile = dict(profiles[selected])
    profile["name"] = selected

    base_url = profile.get("base_url")
    if not base_url:
        raise ValueError(f"Profile {selected} missing base_url")

    api_key = None
    api_key_env = profile.get("api_key_env")
    if api_key_env:
        api_key = os.environ.get(api_key_env)
        if not api_key:
            raise ValueError(f"Profile {selected} requires env var {api_key_env}")
    else:
        api_key = profile.get("api_key")

    if not api_key:
        raise ValueError(f"Profile {selected} missing api_key_env or api_key")

    model = (model_override or "").strip() or profile.get("default_model")
    if not model:
        raise ValueError(f"Profile {selected} missing default_model and model_override is empty")

    profile["api_key"] = api_key
    profile["model"] = model
    return profile
