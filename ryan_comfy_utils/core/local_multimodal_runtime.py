from __future__ import annotations

import atexit
import gc
import json
import os
import shutil
import socket
import subprocess
import tempfile
import threading
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import folder_paths

from .image_utils import pil_to_data_url

MODEL_FOLDER_NAME = "ryan_multimodal"
DEFAULT_MODEL_ROOT = Path(folder_paths.models_dir) / MODEL_FOLDER_NAME
MODEL_NONE = "[no local multimodal model found]"
MMPROJ_AUTO = "auto"

try:
    folder_paths.add_model_folder_path(MODEL_FOLDER_NAME, str(DEFAULT_MODEL_ROOT), is_default=True)
except TypeError:
    # Compatibility with older ComfyUI versions without the is_default argument.
    folder_paths.add_model_folder_path(MODEL_FOLDER_NAME, str(DEFAULT_MODEL_ROOT))


def _model_roots() -> list[Path]:
    roots: list[Path] = []
    try:
        configured = folder_paths.get_folder_paths(MODEL_FOLDER_NAME)
    except Exception:
        configured = [str(DEFAULT_MODEL_ROOT)]
    for value in configured:
        path = Path(value).expanduser().resolve()
        if path not in roots:
            roots.append(path)
    return roots


def ensure_model_root() -> Path:
    DEFAULT_MODEL_ROOT.mkdir(parents=True, exist_ok=True)
    return DEFAULT_MODEL_ROOT


def _relative_display(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.name


def _looks_like_mmproj(path: Path) -> bool:
    name = path.name.lower()
    return any(token in name for token in ("mmproj", "projector", "vision-proj", "vision_proj", "clip-model", "clip_model"))


def list_local_model_choices() -> list[str]:
    ensure_model_root()
    choices: set[str] = set()
    for root in _model_roots():
        if not root.is_dir():
            continue
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [name for name in dirnames if name not in {".git", "__pycache__"}]
            current = Path(dirpath)
            if "config.json" in filenames:
                choices.add(f"HF | {_relative_display(current, root)}")
            for filename in filenames:
                path = current / filename
                if path.suffix.lower() == ".gguf" and not _looks_like_mmproj(path):
                    choices.add(f"GGUF | {_relative_display(path, root)}")
    return sorted(choices) or [MODEL_NONE]


def list_mmproj_choices() -> list[str]:
    ensure_model_root()
    choices: set[str] = {MMPROJ_AUTO}
    for root in _model_roots():
        if not root.is_dir():
            continue
        for path in root.rglob("*.gguf"):
            if path.is_file() and _looks_like_mmproj(path):
                choices.add(_relative_display(path, root))
    return [MMPROJ_AUTO] + sorted(item for item in choices if item != MMPROJ_AUTO)


def _resolve_relative_path(relative: str, *, require_file: bool | None = None) -> Path:
    normalized = Path(relative)
    if normalized.is_absolute() or ".." in normalized.parts:
        raise ValueError(f"Unsafe model selector path: {relative!r}")
    for root in _model_roots():
        candidate = (root / normalized).resolve()
        try:
            candidate.relative_to(root.resolve())
        except ValueError:
            continue
        if not candidate.exists():
            continue
        if require_file is True and not candidate.is_file():
            continue
        if require_file is False and not candidate.is_dir():
            continue
        return candidate
    raise FileNotFoundError(f"Local multimodal model path not found: {relative}")


def resolve_model_path(selection: str, path_override: str = "") -> tuple[str, Path]:
    override = (path_override or "").strip().strip('"')
    if override:
        path = Path(os.path.expandvars(os.path.expanduser(override))).resolve()
        if not path.exists():
            raise FileNotFoundError(f"model_path_override does not exist: {path}")
        backend = "llama_cpp" if path.is_file() and path.suffix.lower() == ".gguf" else "transformers"
        return backend, path

    if not selection or selection == MODEL_NONE:
        raise FileNotFoundError(
            f"No model selected. Place a Transformers model directory or GGUF files under {ensure_model_root()}"
        )
    if selection.startswith("HF | "):
        return "transformers", _resolve_relative_path(selection[5:], require_file=False)
    if selection.startswith("GGUF | "):
        return "llama_cpp", _resolve_relative_path(selection[7:], require_file=True)
    raise ValueError(f"Unsupported model selector value: {selection}")


def _mmproj_score(candidate: Path, model_path: Path) -> tuple[int, str]:
    name = candidate.name.lower()
    score = 0
    if "mmproj" in name:
        score += 100
    if "projector" in name:
        score += 80
    model_tokens = [token for token in model_path.stem.lower().replace("_", "-").split("-") if len(token) >= 3]
    score += sum(3 for token in model_tokens if token in name)
    return score, name


def resolve_mmproj_path(selection: str, path_override: str, model_path: Path, *, required: bool) -> Path | None:
    override = (path_override or "").strip().strip('"')
    if override:
        path = Path(os.path.expandvars(os.path.expanduser(override))).resolve()
        if not path.is_file():
            raise FileNotFoundError(f"mmproj_path_override is not a file: {path}")
        return path

    if selection and selection != MMPROJ_AUTO:
        return _resolve_relative_path(selection, require_file=True)

    candidates = [path for path in model_path.parent.glob("*.gguf") if path != model_path and _looks_like_mmproj(path)]
    if candidates:
        return sorted(candidates, key=lambda item: _mmproj_score(item, model_path), reverse=True)[0]
    if required:
        raise FileNotFoundError(
            "No mmproj GGUF found next to the selected model. Put a matching mmproj file in the same directory, "
            "select it explicitly, or set mmproj_path_override."
        )
    return None


def find_llama_server(explicit_path: str = "") -> Path:
    values = [explicit_path, os.environ.get("RYAN_LLAMA_SERVER_PATH", "")]
    for value in values:
        value = (value or "").strip().strip('"')
        if not value:
            continue
        path = Path(os.path.expandvars(os.path.expanduser(value))).resolve()
        if path.is_file():
            return path
        raise FileNotFoundError(f"llama-server executable not found: {path}")

    for command in ("llama-server", "llama-server.exe"):
        found = shutil.which(command)
        if found:
            return Path(found).resolve()

    comfy_root = Path(getattr(folder_paths, "base_path", Path(folder_paths.models_dir).parent))
    common_candidates = (
        comfy_root / "llama.cpp" / "llama-server",
        comfy_root / "llama.cpp" / "llama-server.exe",
        comfy_root / "llama.cpp" / "build" / "bin" / "llama-server",
        comfy_root / "llama.cpp" / "build" / "bin" / "Release" / "llama-server.exe",
    )
    for candidate in common_candidates:
        if candidate.is_file():
            return candidate.resolve()

    raise FileNotFoundError(
        "llama-server was not found. Set llama_server_path, set RYAN_LLAMA_SERVER_PATH, "
        "or add the official llama.cpp binary directory to PATH."
    )


def _clear_accelerator_cache() -> None:
    gc.collect()
    try:
        import torch

        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            try:
                torch.cuda.ipc_collect()
            except Exception:
                pass
        mps = getattr(torch, "mps", None)
        if mps is not None and hasattr(mps, "empty_cache"):
            try:
                mps.empty_cache()
            except Exception:
                pass
    except Exception:
        pass


@dataclass
class _LlamaServerSession:
    signature: tuple[Any, ...]
    process: subprocess.Popen
    port: int
    alias: str
    log_file: Any

    @property
    def base_url(self) -> str:
        return f"http://127.0.0.1:{self.port}/v1"


_LIVE_PROCESSES: set[subprocess.Popen] = set()
_LIVE_PROCESSES_LOCK = threading.Lock()


def _register_process(process: subprocess.Popen) -> None:
    with _LIVE_PROCESSES_LOCK:
        _LIVE_PROCESSES.add(process)


def _unregister_process(process: subprocess.Popen) -> None:
    with _LIVE_PROCESSES_LOCK:
        _LIVE_PROCESSES.discard(process)


def _terminate_process(process: subprocess.Popen) -> None:
    if process.poll() is not None:
        _unregister_process(process)
        return
    try:
        process.terminate()
        process.wait(timeout=10)
    except Exception:
        try:
            process.kill()
            process.wait(timeout=5)
        except Exception:
            pass
    finally:
        _unregister_process(process)


def _cleanup_processes() -> None:
    with _LIVE_PROCESSES_LOCK:
        processes = list(_LIVE_PROCESSES)
    for process in processes:
        _terminate_process(process)


atexit.register(_cleanup_processes)


def _free_tcp_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _read_log_tail(log_file: Any, max_bytes: int = 12000) -> str:
    try:
        log_file.flush()
        log_file.seek(0, os.SEEK_END)
        size = log_file.tell()
        log_file.seek(max(0, size - max_bytes))
        data = log_file.read()
        if isinstance(data, bytes):
            return data.decode("utf-8", errors="replace")
        return str(data)
    except Exception:
        return ""


def _wait_for_llama_server(session: _LlamaServerSession, timeout_seconds: int) -> None:
    deadline = time.monotonic() + max(5, int(timeout_seconds))
    last_error = ""
    urls = [f"http://127.0.0.1:{session.port}/health", f"{session.base_url}/models"]
    while time.monotonic() < deadline:
        exit_code = session.process.poll()
        if exit_code is not None:
            log_tail = _read_log_tail(session.log_file)
            raise RuntimeError(f"llama-server exited during startup with code {exit_code}.\n{log_tail}")
        for url in urls:
            try:
                with urllib.request.urlopen(url, timeout=2) as response:
                    if 200 <= response.status < 300:
                        return
            except urllib.error.HTTPError as exc:
                last_error = f"HTTP {exc.code} from {url}"
            except Exception as exc:
                last_error = str(exc)
        time.sleep(0.25)
    log_tail = _read_log_tail(session.log_file)
    raise TimeoutError(f"llama-server did not become ready: {last_error}\n{log_tail}")


def _normalize_gpu_layers(value: str | int) -> str:
    text = str(value).strip().lower()
    if text in {"auto", "all"}:
        return text
    try:
        return str(int(text))
    except ValueError as exc:
        raise ValueError("gpu_layers must be 'auto', 'all', or an integer") from exc


class LocalMultimodalRuntime:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._hf_model = None
        self._hf_processor = None
        self._hf_signature: tuple[Any, ...] | None = None
        self._llama_session: _LlamaServerSession | None = None

    def close(self) -> None:
        with self._lock:
            self.unload_transformers()
            self.stop_llama_server()

    def __del__(self) -> None:
        try:
            self.close()
        except Exception:
            pass

    def unload_transformers(self) -> None:
        self._hf_model = None
        self._hf_processor = None
        self._hf_signature = None
        _clear_accelerator_cache()

    def stop_llama_server(self) -> None:
        session = self._llama_session
        self._llama_session = None
        if session is None:
            return
        _terminate_process(session.process)
        try:
            session.log_file.close()
        except Exception:
            pass
        _clear_accelerator_cache()

    def _load_transformers(
        self,
        model_path: Path,
        *,
        dtype_name: str,
        quantization: str,
        attention: str,
        trust_remote_code: bool,
    ) -> tuple[Any, Any, float]:
        signature = (str(model_path), dtype_name, quantization, attention, bool(trust_remote_code))
        if self._hf_signature == signature and self._hf_model is not None and self._hf_processor is not None:
            return self._hf_model, self._hf_processor, 0.0

        self.unload_transformers()
        started = time.perf_counter()
        try:
            import torch
            from transformers import AutoModelForImageTextToText, AutoProcessor
        except ImportError as exc:
            raise RuntimeError(
                "Transformers backend requires transformers and accelerate. Install requirements-local-multimodal.txt."
            ) from exc

        dtype_map = {
            "auto": "auto",
            "float16": torch.float16,
            "bfloat16": torch.bfloat16,
            "float32": torch.float32,
        }
        if dtype_name not in dtype_map:
            raise ValueError(f"Unsupported dtype: {dtype_name}")

        model_kwargs: dict[str, Any] = {
            "device_map": "auto",
            "trust_remote_code": bool(trust_remote_code),
            "local_files_only": True,
        }
        if attention and attention != "auto":
            model_kwargs["attn_implementation"] = attention
        if quantization in {"4bit", "8bit"}:
            try:
                from transformers import BitsAndBytesConfig
            except ImportError as exc:
                raise RuntimeError("4bit/8bit loading requires bitsandbytes") from exc
            model_kwargs["quantization_config"] = BitsAndBytesConfig(
                load_in_4bit=quantization == "4bit",
                load_in_8bit=quantization == "8bit",
            )

        dtype_value = dtype_map[dtype_name]
        try:
            model = AutoModelForImageTextToText.from_pretrained(model_path, dtype=dtype_value, **model_kwargs)
        except TypeError:
            model = AutoModelForImageTextToText.from_pretrained(model_path, torch_dtype=dtype_value, **model_kwargs)
        processor = AutoProcessor.from_pretrained(
            model_path,
            trust_remote_code=bool(trust_remote_code),
            local_files_only=True,
        )
        model.eval()
        self._hf_model = model
        self._hf_processor = processor
        self._hf_signature = signature
        return model, processor, time.perf_counter() - started

    def run_transformers(
        self,
        *,
        model_path: Path,
        images: list[Any],
        system_prompt: str,
        user_prompt: str,
        temperature: float,
        top_p: float,
        max_new_tokens: int,
        seed: int,
        dtype_name: str,
        quantization: str,
        attention: str,
        trust_remote_code: bool,
        keep_model_loaded: bool,
    ) -> tuple[str, dict[str, Any]]:
        with self._lock:
            model = processor = inputs = generated = trimmed = None
            load_seconds = 0.0
            started = time.perf_counter()
            try:
                model, processor, load_seconds = self._load_transformers(
                    model_path,
                    dtype_name=dtype_name,
                    quantization=quantization,
                    attention=attention,
                    trust_remote_code=trust_remote_code,
                )
                import torch

                if int(seed) >= 0:
                    torch.manual_seed(int(seed))
                    if torch.cuda.is_available():
                        torch.cuda.manual_seed_all(int(seed))

                messages: list[dict[str, Any]] = []
                if system_prompt.strip():
                    messages.append({"role": "system", "content": [{"type": "text", "text": system_prompt}]})
                user_content = [{"type": "image", "image": image} for image in images]
                user_content.append({"type": "text", "text": user_prompt or ""})
                messages.append({"role": "user", "content": user_content})

                inputs = processor.apply_chat_template(
                    messages,
                    add_generation_prompt=True,
                    tokenize=True,
                    return_dict=True,
                    return_tensors="pt",
                )
                target_device = getattr(model, "device", None)
                if target_device is not None and hasattr(inputs, "to"):
                    inputs = inputs.to(target_device)

                generate_kwargs: dict[str, Any] = {
                    "max_new_tokens": int(max_new_tokens),
                    "do_sample": float(temperature) > 0,
                }
                if float(temperature) > 0:
                    generate_kwargs["temperature"] = float(temperature)
                    generate_kwargs["top_p"] = float(top_p)

                with torch.inference_mode():
                    generated = model.generate(**inputs, **generate_kwargs)
                prompt_length = int(inputs["input_ids"].shape[-1])
                trimmed = generated[:, prompt_length:]
                text = processor.batch_decode(trimmed, skip_special_tokens=True, clean_up_tokenization_spaces=False)[0]
                info = {
                    "backend": "transformers",
                    "model_path": str(model_path),
                    "image_count": len(images),
                    "load_seconds": round(load_seconds, 3),
                    "total_seconds": round(time.perf_counter() - started, 3),
                    "kept_loaded": bool(keep_model_loaded),
                    "dtype": dtype_name,
                    "quantization": quantization,
                }
                return text, info
            finally:
                if not keep_model_loaded:
                    # Drop local references before GC / empty_cache; otherwise the
                    # model and generated tensors stay alive until after return.
                    trimmed = generated = inputs = processor = model = None
                    self.unload_transformers()

    def _start_llama_server(
        self,
        *,
        server_path: Path,
        model_path: Path,
        mmproj_path: Path | None,
        context_size: int,
        gpu_layers: str,
        threads: int,
        mmproj_offload: bool,
        startup_timeout_seconds: int,
    ) -> tuple[_LlamaServerSession, float]:
        signature = (
            str(server_path),
            str(model_path),
            str(mmproj_path or ""),
            int(context_size),
            _normalize_gpu_layers(gpu_layers),
            int(threads),
            bool(mmproj_offload),
        )
        session = self._llama_session
        if session is not None and session.signature == signature and session.process.poll() is None:
            return session, 0.0
        self.stop_llama_server()

        port = _free_tcp_port()
        alias = "ryan-local-multimodal"
        command = [
            str(server_path),
            "-m",
            str(model_path),
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
            "--alias",
            alias,
            "--no-webui",
            "-ngl",
            _normalize_gpu_layers(gpu_layers),
        ]
        if mmproj_path is not None:
            command += ["--mmproj", str(mmproj_path)]
        if not mmproj_offload:
            command.append("--no-mmproj-offload")
        if int(context_size) > 0:
            command += ["-c", str(int(context_size))]
        if int(threads) > 0:
            command += ["--threads", str(int(threads))]

        log_file = tempfile.TemporaryFile(mode="w+b")
        popen_kwargs: dict[str, Any] = {
            "stdin": subprocess.DEVNULL,
            "stdout": log_file,
            "stderr": subprocess.STDOUT,
            "cwd": str(server_path.parent),
        }
        if os.name == "nt":
            popen_kwargs["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0)

        started = time.perf_counter()
        try:
            process = subprocess.Popen(command, **popen_kwargs)
        except Exception:
            log_file.close()
            raise
        _register_process(process)
        session = _LlamaServerSession(signature=signature, process=process, port=port, alias=alias, log_file=log_file)
        self._llama_session = session
        try:
            _wait_for_llama_server(session, startup_timeout_seconds)
        except Exception:
            self.stop_llama_server()
            raise
        return session, time.perf_counter() - started

    def run_llama_cpp(
        self,
        *,
        server_path: Path,
        model_path: Path,
        mmproj_path: Path | None,
        images: list[Any],
        system_prompt: str,
        user_prompt: str,
        temperature: float,
        top_p: float,
        max_new_tokens: int,
        seed: int,
        context_size: int,
        gpu_layers: str,
        threads: int,
        mmproj_offload: bool,
        startup_timeout_seconds: int,
        request_timeout_seconds: int,
        keep_model_loaded: bool,
    ) -> tuple[str, dict[str, Any]]:
        with self._lock:
            started = time.perf_counter()
            try:
                session, load_seconds = self._start_llama_server(
                    server_path=server_path,
                    model_path=model_path,
                    mmproj_path=mmproj_path,
                    context_size=context_size,
                    gpu_layers=gpu_layers,
                    threads=threads,
                    mmproj_offload=mmproj_offload,
                    startup_timeout_seconds=startup_timeout_seconds,
                )
                try:
                    from openai import OpenAI
                except ImportError as exc:
                    raise RuntimeError("GGUF backend requires openai>=1.0.0") from exc

                content: list[dict[str, Any]] = []
                for image in images:
                    content.append({
                        "type": "image_url",
                        "image_url": {"url": pil_to_data_url(image, "jpeg", 90)},
                    })
                content.append({"type": "text", "text": user_prompt or ""})
                messages: list[dict[str, Any]] = []
                if system_prompt.strip():
                    messages.append({"role": "system", "content": system_prompt})
                messages.append({"role": "user", "content": content})

                client = OpenAI(base_url=session.base_url, api_key="not-needed", timeout=float(request_timeout_seconds))
                request: dict[str, Any] = {
                    "model": session.alias,
                    "messages": messages,
                    "temperature": float(temperature),
                    "top_p": float(top_p),
                    "max_tokens": int(max_new_tokens),
                    "stream": False,
                }
                if int(seed) >= 0:
                    request["seed"] = int(seed)
                try:
                    response = client.chat.completions.create(**request)
                finally:
                    client.close()
                text = response.choices[0].message.content or ""
                info = {
                    "backend": "llama_cpp_server",
                    "model_path": str(model_path),
                    "mmproj_path": str(mmproj_path) if mmproj_path else "",
                    "llama_server_path": str(server_path),
                    "image_count": len(images),
                    "load_seconds": round(load_seconds, 3),
                    "total_seconds": round(time.perf_counter() - started, 3),
                    "kept_loaded": bool(keep_model_loaded),
                    "port": session.port if keep_model_loaded else None,
                }
                return text, info
            except Exception:
                if keep_model_loaded:
                    self.stop_llama_server()
                raise
            finally:
                if not keep_model_loaded:
                    self.stop_llama_server()

    @staticmethod
    def info_json(info: dict[str, Any]) -> str:
        return json.dumps(info, ensure_ascii=False, indent=2)
