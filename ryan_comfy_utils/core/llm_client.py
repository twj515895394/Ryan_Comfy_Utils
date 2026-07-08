import json
from typing import Any, Dict, List, Optional

from openai import OpenAI

from .config_loader import resolve_profile


def _to_json_text(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, default=str)


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
        extra_body_json: Optional[str] = None,
    ):
        extra_body = None
        if extra_body_json and extra_body_json.strip():
            extra_body = json.loads(extra_body_json)

        request_payload = {
            "model": self.profile["model"],
            "messages": messages,
            "temperature": float(temperature),
            "max_tokens": int(max_tokens),
            "top_p": float(top_p),
            "stream": False,
        }
        if extra_body:
            request_payload.update(extra_body)

        last_error = None
        attempts = max(0, int(retry_count or 0)) + 1
        for _ in range(attempts):
            try:
                response = self.client.chat.completions.create(**request_payload)
                raw = response.model_dump() if hasattr(response, "model_dump") else response
                text = response.choices[0].message.content or ""
                return text, _to_json_text(request_payload), _to_json_text(raw)
            except Exception as exc:
                last_error = exc
        raise RuntimeError(f"Ryan LLM request failed: {last_error}")
