import json

from ..core.config_loader import list_profile_names
from ..core.image_utils import pil_to_data_url, resize_max_side, tensor_batch_to_pil
from ..core.llm_client import RyanOpenAICompatibleClient


def _profiles():
    try:
        return list_profile_names()
    except Exception:
        return ["default"]


class RyanLLMChat:
    @classmethod
    def INPUT_TYPES(cls):
        profiles = _profiles()
        return {
            "required": {
                "profile": (profiles,),
                "model_override": ("STRING", {"default": ""}),
                "system_prompt": ("STRING", {"default": "", "multiline": True}),
                "user_prompt": ("STRING", {"default": "", "multiline": True}),
                "temperature": ("FLOAT", {"default": 0.7, "min": 0, "max": 2, "step": 0.01}),
                "max_tokens": ("INT", {"default": 4096, "min": 1, "max": 128000, "step": 1}),
                "top_p": ("FLOAT", {"default": 1.0, "min": 0, "max": 1, "step": 0.01}),
                "timeout_seconds": ("INT", {"default": 300, "min": 30, "max": 1200, "step": 10}),
                "retry_count": ("INT", {"default": 0, "min": 0, "max": 3, "step": 1}),
                "extra_body_json": ("STRING", {"default": "", "multiline": True}),
            }
        }

    RETURN_TYPES = ("STRING", "STRING", "STRING")
    RETURN_NAMES = ("response_text", "request_json", "raw_response_json")
    FUNCTION = "run"
    CATEGORY = "Ryan Utils / LLM"

    def run(self, profile, model_override, system_prompt, user_prompt, temperature, max_tokens, top_p, timeout_seconds, retry_count, extra_body_json):
        messages = []
        if system_prompt and system_prompt.strip():
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": user_prompt or ""})

        client = RyanOpenAICompatibleClient(profile, model_override, timeout_seconds)
        return client.chat(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            top_p=top_p,
            retry_count=retry_count,
            extra_body_json=extra_body_json,
        )


class RyanLLMVisionChat:
    @classmethod
    def INPUT_TYPES(cls):
        profiles = _profiles()
        return {
            "required": {
                "profile": (profiles,),
                "model_override": ("STRING", {"default": ""}),
                "system_prompt": ("STRING", {"default": "", "multiline": True}),
                "user_prompt": ("STRING", {"default": "", "multiline": True}),
                "temperature": ("FLOAT", {"default": 0.7, "min": 0, "max": 2, "step": 0.01}),
                "max_tokens": ("INT", {"default": 4096, "min": 1, "max": 128000, "step": 1}),
                "top_p": ("FLOAT", {"default": 1.0, "min": 0, "max": 1, "step": 0.01}),
                "timeout_seconds": ("INT", {"default": 300, "min": 30, "max": 1200, "step": 10}),
                "retry_count": ("INT", {"default": 0, "min": 0, "max": 3, "step": 1}),
                "max_images": ("INT", {"default": 10, "min": 1, "max": 10, "step": 1}),
                "image_max_side": ("INT", {"default": 1280, "min": 256, "max": 4096, "step": 64}),
                "image_format": (["jpeg", "png"], {"default": "jpeg"}),
                "jpeg_quality": ("INT", {"default": 85, "min": 50, "max": 100, "step": 1}),
                "extra_body_json": ("STRING", {"default": "", "multiline": True}),
            },
            "optional": {
                "images": ("IMAGE",),
            }
        }

    RETURN_TYPES = ("STRING", "STRING", "STRING")
    RETURN_NAMES = ("response_text", "request_json", "raw_response_json")
    FUNCTION = "run"
    CATEGORY = "Ryan Utils / LLM"

    def run(self, profile, model_override, system_prompt, user_prompt, temperature, max_tokens, top_p, timeout_seconds, retry_count, max_images, image_max_side, image_format, jpeg_quality, extra_body_json, images=None):
        content = []
        pil_images = tensor_batch_to_pil(images)[: int(max_images or 10)] if images is not None else []
        for img in pil_images:
            resized = resize_max_side(img, image_max_side)
            content.append({
                "type": "image_url",
                "image_url": {"url": pil_to_data_url(resized, image_format, jpeg_quality)},
            })
        content.append({"type": "text", "text": user_prompt or ""})

        messages = []
        if system_prompt and system_prompt.strip():
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": content})

        client = RyanOpenAICompatibleClient(profile, model_override, timeout_seconds)
        return client.chat(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            top_p=top_p,
            retry_count=retry_count,
            extra_body_json=extra_body_json,
        )
