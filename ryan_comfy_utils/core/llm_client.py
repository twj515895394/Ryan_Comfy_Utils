import copy
import json
from typing import Any, Dict, List, Optional

from openai import OpenAI

from .config_loader import resolve_profile


DATA_URL_PREFIX = "data:image/"
DEFAULT_DEBUG_IMAGE_PREFIX_CHARS = 120


def _to_json_text(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, default=str)


def _truncate_data_url(value: str, prefix_chars: int = DEFAULT_DEBUG_IMAGE_PREFIX_CHARS) -> str:
    if not isinstance(value, str) or not value.startswith(DATA_URL_PREFIX):
        return value
    return f"{value[:prefix_chars]}...<base64_truncated, original_chars={len(value)}>"


def _sanitize_for_debug(value: Any) -> Any:
    """Return a debug-safe copy of the request payload.

    Vision requests may contain very large base64 data URLs. Keeping the full
    data in request_json makes ComfyUI output unreadable and can make workflow
    json extremely large, so only debug output is truncated. The real request is
    still sent with the complete base64 image content.
    """
    if isinstance(value, dict):
        return {k: _sanitize_for_debug(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_sanitize_for_debug(item) for item in value]
    if isinstance(value, str):
        return _truncate_data_url(value)
    return value


class RyanOpenAICompatibleClient:
    def __init__(self, profile_name: str, model_override: str = "", timeout_seconds: int = 300):
        self.profile = resolve_profile(profile_name, model_override)
        self.timeout_seconds = int(timeout_seconds or 300)
        self.client = OpenAI(
            api_key=self.profile["api_key"],
            base_url=self.profile["base_url"],
            timeout=self.timeout_seconds,
        )

    def chat(
        self,
        messages: List[Dict[str, Any]],
        temperature: float = 0.7,
        max_tokens: int = 4096,
        top_p: float = 1.0,
        retry_count: int = 0,
        disable_thinking: bool = False,
        extra_body_json: Optional[str] = None,
    ):
        extra_body = {}
        if disable_thinking:
            extra_body["enable_thinking"] = False
            extra_body["reasoning"] = {"exclude": True}

        request_payload = {
            "model": self.profile["model"],
            "messages": messages,
            "temperature": float(temperature),
            "max_tokens": int(max_tokens),
            "top_p": float(top_p),
            "stream": False,
        }

        if extra_body_json and extra_body_json.strip():
            user_extra = json.loads(extra_body_json)
            if isinstance(user_extra, dict):
                request_payload.update(user_extra)

        if extra_body:
            request_payload["extra_body"] = extra_body

        debug_request_payload = _sanitize_for_debug(copy.deepcopy(request_payload))

        last_error = None
        attempts = max(0, int(retry_count or 0)) + 1
        for _ in range(attempts):
            try:
                response = self.client.chat.completions.create(**request_payload)
                raw = response.model_dump() if hasattr(response, "model_dump") else response
                text = response.choices[0].message.content or ""
                return text, _to_json_text(debug_request_payload), _to_json_text(raw)
            except Exception as exc:
                last_error = exc
        raise RuntimeError(f"Ryan LLM request failed: {last_error}")
