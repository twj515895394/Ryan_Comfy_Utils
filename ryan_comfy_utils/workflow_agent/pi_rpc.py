"""Workflow Agent 的 Pi ``--mode rpc`` 运行边界。

该模块只负责进程边界：命令构造、能力检查、增量事件归一化和停止句柄。
业务状态由 chat/commit service 持久化，避免把私有 Chat 混入 RYAN_CONTEXT。
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
from queue import Empty, Queue

import threading
import time
from pathlib import Path
from typing import Any, Callable, Iterable, Iterator, Mapping

from ..acp.pi_runner import RYAN_SYSTEM_PROMPT

_PI_TOOLS = "read,bash,edit,write"
_REQUIRED_FLAGS = ("--mode", "--no-context-files", "--skill")


class PiRpcError(RuntimeError):
    """Pi RPC 运行失败。"""


class PiCapabilityError(PiRpcError):
    """Pi CLI 不具备 RPC 所需能力。"""


class PiRpcTimeoutError(PiRpcError):
    """Pi RPC 超时。"""


class PiRpcInterruptedError(PiRpcError):
    """Pi RPC 被停止。"""

def _resolve_executable(command: list[str]) -> list[str]:
    """在 Windows 上把 ``pi`` 解析为可直接 CreateProcess 的 .cmd/.exe。"""
    if not command or os.name != "nt":
        return command
    executable = shutil.which(command[0])
    if executable:
        return [executable, *command[1:]]
    return command



def _replace_placeholders(command: list[str], *, skill_directory: Path, system_prompt: str) -> list[str]:
    values = {"{skill_directory}": str(skill_directory), "{ryan_system_prompt}": system_prompt}
    return [values.get(part, part) for part in command]


def _option_index(command: list[str], flag: str) -> int | None:
    try:
        return command.index(flag)
    except ValueError:
        return None


def _ensure_option(command: list[str], flag: str, value: str, *, required_value: bool = True) -> None:
    index = _option_index(command, flag)
    if index is None:
        command.extend((flag, value) if required_value else (flag,))
        return
    if required_value and (index + 1 >= len(command) or command[index + 1].startswith("-")):
        command.insert(index + 1, value)


def build_pi_rpc_command(
    runner_profile: Mapping[str, Any] | None,
    skill_directory: str | Path,
    *,
    mode: str = "DISCUSS",
    system_prompt: str = RYAN_SYSTEM_PROMPT,
) -> list[str]:
    """构造 RPC 命令；Provider/Model 不由项目 Profile 固定。"""
    profile = dict(runner_profile or {})
    raw = profile.get("command") or ["pi"]
    command = [str(value) for value in raw if str(value) not in {"{context}", "{prompt}"}]
    if not command or not command[0].strip():
        raise PiCapabilityError("Pi RPC command is not configured")
    if profile.get("runner") not in (None, "pi_cli", "pi"):
        raise PiCapabilityError("configured runner is not Pi")
    configured_prompt = profile.get("system_prompt") or system_prompt
    if configured_prompt == "{ryan_system_prompt}":
        configured_prompt = system_prompt
    prompt = f"{configured_prompt.rstrip()}\n\nRYAN_AGENT_MODE={str(mode).upper()}"
    command = _replace_placeholders(command, skill_directory=Path(skill_directory), system_prompt=prompt)
    _ensure_option(command, "--mode", "rpc")
    mode_index = _option_index(command, "--mode")
    if mode_index is None or mode_index + 1 >= len(command) or command[mode_index + 1] != "rpc":
        raise PiCapabilityError("Pi RPC command requires --mode rpc")
    if "--no-context-files" not in command:
        command.append("--no-context-files")
    # RPC 请求由本服务持久化；禁止 Pi 复用全局会话或等待项目授权，
    # 否则不同 Agent 的并发请求可能共享会话锁，或在无 UI 的 RPC 模式停住。
    if "--no-session" not in command:
        command.append("--no-session")
    if "--approve" not in command and "--no-approve" not in command:
        command.append("--approve")
    if "--skill" not in command:
        command.extend(("--skill", str(Path(skill_directory))))
    else:
        index = command.index("--skill")
        if index + 1 >= len(command) or command[index + 1].startswith("-"):
            command.insert(index + 1, str(Path(skill_directory)))
    _ensure_option(command, "--system-prompt", prompt)
    index = _option_index(command, "--system-prompt")
    if index is not None and index + 1 < len(command) and command[index + 1] == "{ryan_system_prompt}":
        command[index + 1] = prompt
    if profile.get("tool_policy", "full") == "full" and "--tools" not in command:
        command.extend(("--tools", _PI_TOOLS))
    elif profile.get("tool_policy", "full") not in (None, "full"):
        raise PiCapabilityError("unsupported Pi tool policy")
    return command


build_rpc_command = build_pi_rpc_command


def probe_pi_rpc_cli(command: Iterable[str], timeout_seconds: float = 10) -> None:
    """检查 Pi 可执行文件和 RPC 必要参数，不回退到 Claude。"""
    args = _resolve_executable([str(item) for item in command])
    if not args or not args[0].strip():
        raise PiCapabilityError("Pi CLI capability check failed")
    executable = args[0]
    if shutil.which(executable) is None and not Path(executable).expanduser().exists():
        raise PiCapabilityError("Pi CLI is not available")
    try:
        completed = subprocess.run(
            [executable, "--help"], capture_output=True, text=True, check=False,
            timeout=timeout_seconds, encoding="utf-8", shell=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise PiRpcTimeoutError("Pi CLI capability check timed out") from exc
    except OSError as exc:
        raise PiCapabilityError("Pi CLI capability check failed") from exc
    help_text = f"{completed.stdout}\n{completed.stderr}"
    missing = [flag for flag in _REQUIRED_FLAGS if flag not in help_text]
    if completed.returncode != 0 or missing:
        raise PiCapabilityError("Pi CLI does not support required RPC options")


def _text_from_event(payload: Mapping[str, Any]) -> str:
    for key in ("text", "delta", "content", "output"):
        value = payload.get(key)
        if isinstance(value, str):
            return value
    message = payload.get("message")
    if isinstance(message, str):
        return message
    if isinstance(message, Mapping):
        return _text_from_event(message)
    return ""


def parse_rpc_event(line: str | bytes | Mapping[str, Any]) -> dict[str, Any] | None:
    """将 Pi JSONL/纯文本行归一化为 UI 可消费事件。"""
    if isinstance(line, Mapping):
        payload: dict[str, Any] = dict(line)
    else:
        text_line = line.decode("utf-8", "replace") if isinstance(line, bytes) else str(line)
        if not text_line.strip():
            return None
        try:
            decoded = json.loads(text_line)
        except (TypeError, json.JSONDecodeError):
            return {"type": "delta", "status": "delta", "text": text_line.rstrip("\r\n")}
        if not isinstance(decoded, Mapping):
            return {"type": "delta", "status": "delta", "text": str(decoded)}
        payload = dict(decoded)
    event_type = str(payload.get("type", payload.get("event", "message")))
    nested = payload.get("assistantMessageEvent") or payload.get("event_data")
    if isinstance(nested, Mapping):
        merged = dict(nested)
        merged.setdefault("type", event_type)
        payload = {**payload, **merged}
    lowered = event_type.lower()
    if any(token in lowered for token in ("error", "failed")):
        status = "error"
    elif any(token in lowered for token in ("end", "done", "complete", "result", "exit")):
        status = "completed"
    elif any(token in lowered for token in ("stop", "interrupt", "abort")):
        status = "stopped"
    else:
        status = "delta" if _text_from_event(payload) else event_type
    result = dict(payload)
    result["type"] = event_type
    result["status"] = status
    text = _text_from_event(payload)
    if text:
        result["text"] = text
    return result

_STREAM_END = object()


def _read_stream(stream: Any, output: Queue[Any]) -> None:
    try:
        for line in iter(stream.readline, ""):
            output.put(line)
    except (OSError, ValueError):
        pass
    finally:
        output.put(_STREAM_END)


def _drain_stream(stream: Any) -> None:
    try:
        for _chunk in iter(stream.readline, ""):
            pass
    except (OSError, ValueError):
        pass




def _assistant_text(value: Any) -> str:
    """提取当前 agent turn 最后的 assistant 文本，避免拼接工具前置回复。"""
    if isinstance(value, Mapping):
        if value.get("role") == "assistant":
            content = value.get("content")
            if isinstance(content, str):
                return content
            if isinstance(content, list):
                return "".join(
                    str(item.get("text", ""))
                    for item in content
                    if isinstance(item, Mapping) and item.get("type") == "text"
                )
        messages = value.get("messages")
        if isinstance(messages, list):
            return _assistant_text(messages)
        return ""
    if isinstance(value, list):
        for item in reversed(value):
            text = _assistant_text(item)
            if text:
                return text
    return ""



def _rpc_event_error(event: Mapping[str, Any]) -> str:
    if event.get("type") == "response" and event.get("success") is False:
        return str(event.get("error") or "Pi RPC command failed")
    if event.get("status") == "error":
        return str(event.get("error") or event.get("errorMessage") or "Pi RPC failed")
    for key in ("error", "errorMessage", "error_message"):
        value = event.get(key)
        if isinstance(value, str) and value.strip():
            return value
    for key in ("message", "assistantMessageEvent"):
        value = event.get(key)
        if isinstance(value, Mapping):
            nested = _rpc_event_error(value)
            if nested:
                return nested
    for value in event.get("messages", []) if isinstance(event.get("messages"), list) else []:
        if isinstance(value, Mapping):
            nested = _rpc_event_error(value)
            if nested:
                return nested
    if str(event.get("stopReason", "")).lower() == "error":
        return "Pi assistant response failed"
    return ""


class PiRpcRunner:
    """同步、可停止的 Pi RPC 进程包装器。"""

    def __init__(self, profile: Mapping[str, Any] | None = None, *, probe: bool = True) -> None:
        self.profile = dict(profile or {})
        self.probe = probe
        self.status = "idle"
        self.stop_handle: subprocess.Popen[str] | None = None
        self._process: subprocess.Popen[str] | None = None
        self._lock = threading.Lock()

    def run(
        self,
        *,
        skill_directory: str | Path,
        session_dir: str | Path,
        prompt: str,
        mode: str = "DISCUSS",
        timeout_seconds: float | None = None,
        on_event: Callable[[dict[str, Any]], None] | None = None,
    ) -> Iterator[dict[str, Any]]:
        command = build_pi_rpc_command(self.profile, skill_directory, mode=mode)
        if self.probe:
            probe_pi_rpc_cli(command, float(self.profile.get("probe_timeout_seconds", 10)))
        timeout = timeout_seconds if timeout_seconds is not None else float(self.profile.get("timeout_seconds", 300))
        process: subprocess.Popen[str] | None = None
        start = time.monotonic()
        settled = False
        saw_text = False


        intentional_shutdown = False
        stdout_thread: threading.Thread | None = None
        stderr_thread: threading.Thread | None = None

        def terminate_process() -> None:
            if process is None or process.poll() is not None:
                return
            try:
                process.terminate()
                process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
            except OSError:
                return

        self.status = "generating"
        try:
            process = subprocess.Popen(
                _resolve_executable(command), cwd=str(Path(session_dir)), stdin=subprocess.PIPE,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                encoding="utf-8", errors="replace", shell=False,
            )
            with self._lock:
                self._process = process
                self.stop_handle = process
            assert process.stdin is not None
            process.stdin.write(json.dumps(
                {"type": "prompt", "message": prompt}, ensure_ascii=False,
            ))
            process.stdin.write("\n")
            process.stdin.flush()
            assert process.stdout is not None
            stdout_queue: Queue[Any] = Queue()
            stdout_thread = threading.Thread(
                target=_read_stream, args=(process.stdout, stdout_queue), daemon=True,
            )
            stdout_thread.start()
            assert process.stderr is not None
            stderr_thread = threading.Thread(
                target=_drain_stream, args=(process.stderr,), daemon=True,
            )
            stderr_thread.start()

            while True:
                remaining = timeout - (time.monotonic() - start)
                if remaining <= 0:
                    self.stop()
                    raise PiRpcTimeoutError("Pi RPC timed out")
                try:
                    line = stdout_queue.get(timeout=min(remaining, 0.5))
                except Empty:
                    continue
                if line is _STREAM_END:
                    break
                event = parse_rpc_event(line)
                if event is None:
                    continue
                error = _rpc_event_error(event)
                if error:
                    self.status = "error"
                    raise PiRpcError(error)
                if event.get("type") == "agent_end":
                    final_text = _assistant_text(event.get("messages"))
                    if final_text:
                        # agent_end 是整轮的权威结果；不要把它再次当作流式 delta。
                        event["final_text"] = final_text
                        if not saw_text:
                            event["text"] = final_text
                if event.get("text"):
                    saw_text = True
                if on_event:
                    on_event(event)
                yield event
                if event.get("type") == "agent_settled":
                    settled = True
                    break

            if settled:
                if process.poll() is None:
                    intentional_shutdown = True
                    terminate_process()
                return_code = process.wait()
                if return_code != 0 and not intentional_shutdown:
                    self.status = "error"
                    raise PiRpcError("Pi RPC exited unsuccessfully")
            else:
                remaining = timeout - (time.monotonic() - start)
                return_code = process.wait(timeout=max(0.0, remaining))
                if self.status == "stopped":
                    raise PiRpcInterruptedError("Pi RPC was stopped")
                self.status = "error"
                if return_code != 0:
                    raise PiRpcError("Pi RPC exited unsuccessfully")
                raise PiRpcError("Pi RPC ended before agent settled")
            self.status = "completed"
        except PiRpcTimeoutError:
            terminate_process()
            self.status = "error"
            raise
        except subprocess.TimeoutExpired as exc:
            self.stop()
            self.status = "error"
            raise PiRpcTimeoutError("Pi RPC timed out") from exc
        except PiRpcError:
            terminate_process()
            raise
        except (BrokenPipeError, OSError) as exc:
            terminate_process()
            self.status = "error"
            raise PiRpcError("Pi RPC could not be started") from exc
        finally:
            for thread in (stdout_thread, stderr_thread):
                if thread is not None:
                    thread.join(timeout=1)
            if process is not None:
                for stream in (process.stdin, process.stdout, process.stderr):
                    if stream is not None:
                        stream.close()
            with self._lock:
                self._process = None
                self.stop_handle = None

    def stop(self) -> bool:
        with self._lock:
            process = self._process or self.stop_handle
        if process is None or process.poll() is not None:
            return False
        self.status = "stopped"
        try:
            process.terminate()
            try:
                process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                process.kill()
        except OSError:
            return False
        return True


__all__ = [
    "PiCapabilityError", "PiRpcError", "PiRpcInterruptedError", "PiRpcRunner",
    "PiRpcTimeoutError", "build_pi_rpc_command", "build_rpc_command",
    "parse_rpc_event", "probe_pi_rpc_cli",
]
