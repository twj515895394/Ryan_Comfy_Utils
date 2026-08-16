import os
import shutil
import subprocess
from pathlib import Path


RYAN_SYSTEM_PROMPT = """你是 Ryan Workflow Agent。
你只能使用当前 Session 工作目录中的内容，以及调用方通过当前请求显式提供的 Context 和 Assets。
DISCUSS 模式用于讨论和形成 Draft；COMMIT 模式才允许输出可供下游消费的正式结果。
不要自行触发 ComfyUI Queue，不要访问其他 Workflow 或 Agent Session，也不要读取 AGENTS.md、CLAUDE.md 等隐式项目规则。
"""

_PI_REQUIRED_HELP_FLAGS = ("--mode", "--no-context-files", "--skill")
_PI_FULL_TOOLS = "read,bash,edit,write"


def _option_value(command: list[str], flag: str) -> str | None:
    try:
        index = command.index(flag)
    except ValueError:
        return None
    if index + 1 >= len(command) or command[index + 1].startswith("-"):
        raise ValueError(f"Pi command option {flag} requires a value")
    return command[index + 1]


def _append_option(command: list[str], flag: str, value: str) -> None:
    existing = _option_value(command, flag)
    if existing is not None:
        if existing != value and flag == "--mode":
            raise ValueError(f"Pi command requires --mode {value}")
        return
    command.extend((flag, value))


def build_pi_command(
    runner_profile: dict,
    skill_directory: Path,
    system_prompt: str = RYAN_SYSTEM_PROMPT,
) -> list[str]:
    """根据 Pi Profile 构造无密钥的 text 命令。"""
    command = [str(arg) for arg in runner_profile.get("command", []) if arg != "{context}"]
    if not command:
        raise ValueError("Pi Profile command must not be empty")
    if runner_profile.get("mode", "text") != "text":
        raise ValueError("Pi ACP runner only supports mode=text")
    if "-p" not in command and "--print" not in command:
        command.append("-p")

    _append_option(command, "--mode", "text")
    if runner_profile.get("no_context_files", True):
        if "--no-context-files" not in command:
            command.append("--no-context-files")
    if runner_profile.get("use_skill_flag", True):
        if "--skill" not in command:
            command.extend(("--skill", "{skill_directory}"))
    configured_prompt = runner_profile.get("system_prompt") or system_prompt
    if configured_prompt == "{ryan_system_prompt}":
        configured_prompt = system_prompt
    if "--system-prompt" in command:
        prompt_index = command.index("--system-prompt") + 1
        if prompt_index >= len(command):
            raise ValueError("Pi command option --system-prompt requires a value")
        if command[prompt_index] == "{ryan_system_prompt}":
            command[prompt_index] = configured_prompt
    _append_option(command, "--system-prompt", configured_prompt)

    tool_policy = runner_profile.get("tool_policy", "full")
    if tool_policy == "full" and "--tools" not in command:
        command.extend(("--tools", _PI_FULL_TOOLS))
    elif tool_policy not in ("full", None):
        raise ValueError(f"Unsupported Pi tool_policy: {tool_policy}")
    return command


def probe_pi_cli(command: list[str], timeout_seconds: int = 10) -> None:
    """检查 Pi 可执行文件及当前版本是否支持 ACP 所需参数。"""
    if not command or not str(command[0]).strip():
        raise RuntimeError("Pi CLI capability check failed: command is empty")
    executable = str(command[0])
    if shutil.which(executable) is None and not Path(executable).expanduser().exists():
        raise RuntimeError(f"Pi CLI is not available: {executable}")
    try:
        completed = subprocess.run(
            [executable, "--help"],
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout_seconds,
            shell=(os.name == "nt"),
            encoding="utf-8",
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(f"Pi CLI capability check timed out after {timeout_seconds}s") from exc
    except OSError as exc:
        raise RuntimeError(f"Pi CLI capability check failed for {executable}: {exc}") from exc

    help_text = f"{completed.stdout}\n{completed.stderr}"
    missing = [flag for flag in _PI_REQUIRED_HELP_FLAGS if flag not in help_text]
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout or "(no output)").strip()
        raise RuntimeError(
            f"Pi CLI capability check failed with returncode={completed.returncode}: {detail[:500]}"
        )
    if missing:
        raise RuntimeError(
            "Pi CLI does not support required ACP options: " + ", ".join(missing)
        )
