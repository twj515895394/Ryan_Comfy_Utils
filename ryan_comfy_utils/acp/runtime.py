import json
from pathlib import Path

from .cli_runner import run_cli_command
from .context_builder import build_context_payload
from .session import create_session_record
from .skill_loader import resolve_skill_directory
from .template_engine import render_context_template
from .workspace import prepare_workspace


def _parse_text_result(result_json_path: Path, stdout_fallback: str, stderr_fallback: str) -> dict:
    if result_json_path.exists():
        return json.loads(result_json_path.read_text(encoding="utf-8"))
    return {
        "status": "ok",
        "outputs": {"response_text": stdout_fallback.strip()},
        "raw_result_json": {
            "stdout": stdout_fallback,
            "stderr": stderr_fallback,
        },
    }


def execute_text_session(
    workspace_root: Path,
    session_id: str,
    skill_root: Path,
    skill_id: str,
    context_template: str,
    user_text: str,
    runner_profile: dict,
) -> dict:
    session_dir = prepare_workspace(workspace_root, session_id)
    skill_directory = resolve_skill_directory(skill_root, skill_id)
    payload = build_context_payload(
        skill_id=skill_id,
        skill_directory=skill_directory,
        user_text=user_text,
        image_paths=[],
        file_paths=[],
        workspace_info={"session_dir": str(session_dir)},
    )
    rendered_context = render_context_template(context_template, payload)
    create_session_record(
        workspace=session_dir,
        runner=runner_profile.get("runner", "unknown"),
        skill_id=skill_id,
        context_payload={"rendered_context": rendered_context, **payload},
    )
    cli_result = run_cli_command(
        command=runner_profile["command"],
        cwd=session_dir,
        timeout_seconds=runner_profile["timeout_seconds"],
        env_overrides=runner_profile.get("environment", {}),
    )
    parsed = _parse_text_result(
        session_dir / "output" / "result.json",
        stdout_fallback=cli_result["stdout"],
        stderr_fallback=cli_result["stderr"],
    )
    parsed["session_dir"] = str(session_dir)
    parsed["raw_result_json"] = cli_result
    return parsed
