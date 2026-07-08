import json
from pathlib import Path


REQUIRED_MANIFEST_KEYS = {
    "node_id",
    "skill_id",
    "mode",
    "context_template",
    "input_contract",
    "output_contract",
    "result_mapping",
}

REQUIRED_PROFILE_KEYS = {
    "runner",
    "command",
    "workspace_root",
    "timeout_seconds",
    "environment",
}


def _load_json(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"JSON root must be object: {path}")
    return data


def load_manifest(path: Path) -> dict:
    data = _load_json(path)
    missing = REQUIRED_MANIFEST_KEYS - set(data.keys())
    if missing:
        raise ValueError(f"Manifest missing keys: {sorted(missing)}")
    return data


def load_profile(path: Path) -> dict:
    data = _load_json(path)
    missing = REQUIRED_PROFILE_KEYS - set(data.keys())
    if missing:
        raise ValueError(f"Profile missing keys: {sorted(missing)}")
    return data


def validate_result_payload(payload: dict) -> dict:
    if "status" not in payload:
        raise ValueError("Result payload missing status")
    if "outputs" not in payload or not isinstance(payload["outputs"], dict):
        raise ValueError("Result payload missing outputs")
    return payload
