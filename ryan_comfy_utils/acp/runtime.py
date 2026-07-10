import json
import subprocess
from pathlib import Path

from .asset_materializer import materialize_input_assets
from .cli_runner import run_cli_command
from .command_expand import expand_cli_command
from .context_builder import build_context_payload
from .contracts import validate_result_payload
from .session import create_session_record
from .skill_loader import resolve_skill_directory
from .template_engine import render_context_template
from .workspace import prepare_workspace

# 失败信息过长时截断，避免 ComfyUI 异常文本爆量
_MAX_ERROR_SNIPPET = 2000

_ERROR_STATUSES = frozenset({"error", "failed"})


def _truncate(text: str, limit: int = _MAX_ERROR_SNIPPET) -> str:
    text = text or ""
    if len(text) <= limit:
        return text
    return text[:limit] + f"...<truncated, original_chars={len(text)}>"


def _resolve_mapping_path(payload: dict, mapping_path: str):
    current = payload
    for part in mapping_path.split("."):
        if not isinstance(current, dict) or part not in current:
            return ""
        current = current[part]
    return current


def map_result_fields(result_payload: dict, result_mapping: dict) -> dict:
    mapped = {}
    for field_name, mapping_path in result_mapping.items():
        mapped[field_name] = _resolve_mapping_path(result_payload, mapping_path)
    return mapped


def _parse_and_validate_result(
    result_json_path: Path,
    stdout_fallback: str,
    stderr_fallback: str,
) -> dict:
    """优先读 result.json；缺失时用 stdout 回退，并统一校验契约。"""
    if result_json_path.exists():
        try:
            payload = json.loads(result_json_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise RuntimeError(
                f"Invalid result.json at {result_json_path}: {exc}"
            ) from exc
        if not isinstance(payload, dict):
            raise RuntimeError(f"result.json root must be object: {result_json_path}")
    else:
        payload = {
            "status": "ok",
            "outputs": {"response_text": (stdout_fallback or "").strip()},
            "raw_result_json": {
                "stdout": stdout_fallback,
                "stderr": stderr_fallback,
            },
        }

    validate_result_payload(payload)

    status = str(payload.get("status", "")).lower()
    if status in _ERROR_STATUSES:
        detail = payload.get("error") or payload.get("message") or payload
        raise RuntimeError(f"ACP result status={status}: {_truncate(str(detail))}")

    return payload


def _raise_for_cli_failure(
    *,
    returncode: int,
    stdout: str,
    stderr: str,
    session_dir: Path,
) -> None:
    if returncode == 0:
        return
    detail = (stderr or "").strip() or (stdout or "").strip() or "(no output)"
    raise RuntimeError(
        f"ACP CLI failed with returncode={returncode} "
        f"session_dir={session_dir}: {_truncate(detail)}"
    )


def execute_text_session(
    workspace_root: Path,
    session_id: str,
    skill_root: Path,
    skill_id: str,
    context_template: str,
    user_text: str,
    runner_profile: dict,
    image_inputs: list[str] | None = None,
    file_inputs: list[str] | None = None,
) -> dict:
    session_dir = prepare_workspace(workspace_root, session_id)
    if skill_id == "none":
        skill_directory = skill_root
    else:
        skill_directory = resolve_skill_directory(skill_root, skill_id)

    assets = materialize_input_assets(
        session_dir=session_dir,
        image_inputs=image_inputs,
        file_inputs=file_inputs,
    )
    payload = build_context_payload(
        skill_id=skill_id,
        skill_directory=skill_directory,
        user_text=user_text,
        image_paths=assets["images"],
        file_paths=assets["files"],
        workspace_info={"session_dir": str(session_dir)},
    )
    if skill_id == "none":
        rendered_context = user_text
    else:
        rendered_context = render_context_template(context_template, payload)

    # 始终落盘 prompt，便于调试与 {context_file} / env 注入（不依赖 command 是否含占位符）
    prompt_path = session_dir / "input" / "prompt.txt"
    prompt_path.write_text(rendered_context, encoding="utf-8")
    prompt_abs = str(prompt_path.resolve())
    session_abs = str(session_dir.resolve())
    skill_abs = str(skill_directory.resolve())

    create_session_record(
        workspace=session_dir,
        runner=runner_profile.get("runner", "unknown"),
        skill_id=skill_id,
        context_payload={"rendered_context": rendered_context, **payload},
    )

    # Filter out "{context}" from the command line arguments list to avoid Windows CLI length limits
    # and newline truncation. Instead, we always pass the context securely via stdin.
    cmd_template = [arg for arg in runner_profile["command"] if arg != "{context}"]

    replacements = {
        "{context_file}": prompt_abs,
        "{session_dir}": session_abs,
        "{skill_directory}": skill_abs,
    }
    command = expand_cli_command(cmd_template, replacements)

    env_overrides = dict(runner_profile.get("environment") or {})
    env_overrides.setdefault("RYAN_ACP_CONTEXT_FILE", prompt_abs)
    env_overrides.setdefault("RYAN_ACP_SESSION_DIR", session_abs)

    timeout_seconds = int(runner_profile["timeout_seconds"])
    try:
        cli_result = run_cli_command(
            command=command,
            cwd=session_dir,
            timeout_seconds=timeout_seconds,
            env_overrides=env_overrides,
            stdin_text=rendered_context,
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(
            f"ACP CLI timed out after {timeout_seconds}s session_dir={session_dir}"
        ) from exc

    _raise_for_cli_failure(
        returncode=cli_result["returncode"],
        stdout=cli_result.get("stdout", ""),
        stderr=cli_result.get("stderr", ""),
        session_dir=session_dir,
    )

    parsed = _parse_and_validate_result(
        session_dir / "output" / "result.json",
        stdout_fallback=cli_result["stdout"],
        stderr_fallback=cli_result["stderr"],
    )
    parsed["session_dir"] = str(session_dir)
    parsed["raw_result_json"] = cli_result
    return parsed
