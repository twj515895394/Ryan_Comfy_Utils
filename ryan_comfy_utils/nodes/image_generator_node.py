import base64
import io
import json
import urllib.request
import urllib.error
from typing import Any, Dict, List
import torch
from PIL import Image

from ..core.config_loader import list_profile_names, resolve_profile
from ..core.image_utils import (
    pil_to_data_url,
    pil_to_tensor_batch,
    tensor_batch_to_pil,
)
from .comfy_image_inputs import build_image_slot_input_types, slots_from_explicit_args


def _profiles():
    try:
        return list_profile_names("image")
    except Exception:
        return ["default"]


class RyanImageGenerator:
    @classmethod
    def INPUT_TYPES(cls):
        profiles = _profiles()
        return {
            "required": {
                "profile": (profiles,),
                "model_override": ("STRING", {"default": ""}),
                "prompt": ("STRING", {"default": "", "multiline": True}),
                "size": (["1024x1024", "512x512", "768x768", "1536x1024", "1024x1536", "1024x576", "576x1024", "2048x2048", "2048x1152", "1152x2048", "3840x2160", "2160x3840", "custom"], {"default": "1024x1024"}),
                "custom_width": ("INT", {"default": 1024, "min": 64, "max": 8192, "step": 8}),
                "custom_height": ("INT", {"default": 1024, "min": 64, "max": 8192, "step": 8}),
                "number_of_images": ("INT", {"default": 1, "min": 1, "max": 10, "step": 1}),
                "response_format": (["auto", "b64_json", "url"], {"default": "auto"}),
                "extra_body_json": ("STRING", {"default": "", "multiline": True}),
            },
            "optional": build_image_slot_input_types(include_paths=False),
        }

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("images",)
    FUNCTION = "generate"
    CATEGORY = "Ryan Utils / Image"
    DESCRIPTION = "图片生成与编辑节点。支持通过文本提示词生成图片，或者接收最多 5 张输入图片以支持图生图/图像编辑。支持从配置文件中选择模型（如 Gemini、GPT、Grok），兼容 standard OpenAI 图像接口。"

    def generate(
        self,
        profile: str,
        model_override: str,
        prompt: str,
        size: str,
        custom_width: int,
        custom_height: int,
        number_of_images: int,
        response_format: str,
        extra_body_json: str,
        image_slot_count: int = 2,
        image_01=None,
        image_02=None,
        image_03=None,
        image_04=None,
        image_05=None,
        image_06=None,
        image_07=None,
        image_08=None,
        image_09=None,
        image_10=None,
    ):
        # 1. 解析 Profile
        profile_data = resolve_profile(profile, model_override)
        api_key = profile_data["api_key"]
        base_url = profile_data["base_url"].rstrip("/")
        model = profile_data["model"]

        # 2. 收集多图输入
        slots = slots_from_explicit_args(
            image_slot_count,
            image_01=image_01,
            image_02=image_02,
            image_03=image_03,
            image_04=image_04,
            image_05=image_05,
            image_06=image_06,
            image_07=image_07,
            image_08=image_08,
            image_09=image_09,
            image_10=image_10,
        )
        # 扁平化槽位张量，转为 PIL 并限制为最多 5 张参考图
        pil_images = []
        for slot in slots:
            if slot is not None:
                pil_images.extend(tensor_batch_to_pil(slot))
        pil_images = pil_images[:5]

        # Check if we should use Chat Completions route (for Gemini models)
        is_chat_route = "gemini" in model.lower()

        # 3. 构造请求 Payload
        if is_chat_route:
            url = f"{base_url}/chat/completions"
            
            # Build chat content
            content = [{"type": "text", "text": prompt}]
            
            # If input images are provided, convert to data URLs and append to content
            for pil_img in pil_images:
                data_url = pil_to_data_url(pil_img, image_format="jpeg")
                content.append({
                    "type": "image_url",
                    "image_url": {"url": data_url}
                })
                
            payload = {
                "model": model,
                "messages": [
                    {
                        "role": "user",
                        "content": content
                    }
                ]
            }
        else:
            url = f"{base_url}/images/generations"
            
            # 转换为 Base64 strings (去除 'data:image/jpeg;base64,' 前缀)
            base64_images = []
            for pil_img in pil_images:
                data_url = pil_to_data_url(pil_img, image_format="jpeg")
                if "," in data_url:
                    base64_str = data_url.split(",", 1)[1]
                    base64_images.append(base64_str)
                    
            final_size = size
            if size == "custom":
                final_size = f"{custom_width}x{custom_height}"

            payload = {
                "model": model,
                "prompt": prompt,
                "n": int(number_of_images),
                "size": final_size,
            }

            if response_format != "auto":
                payload["response_format"] = response_format

            if base64_images:
                payload["images"] = base64_images

        # 合并自定义的额外参数
        if extra_body_json and extra_body_json.strip():
            try:
                extra_params = json.loads(extra_body_json)
                if isinstance(extra_params, dict):
                    payload.update(extra_params)
            except Exception as e:
                raise ValueError(f"Failed to parse extra_body_json: {e}")

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST",
        )

        # 5. 发送请求并解析结果
        timeout = int(profile_data.get("timeout_seconds", 300))
        try:
            with urllib.request.urlopen(req, timeout=timeout) as response:
                resp_json = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as he:
            err_msg = he.read().decode("utf-8")
            raise RuntimeError(f"API request failed with HTTP {he.code}: {err_msg}")
        except Exception as exc:
            raise RuntimeError(f"API request failed: {exc}")

        # 6. 解析响应数据中的图片列表
        output_pil_images = []
        if is_chat_route:
            choices = resp_json.get("choices", [])
            if not choices:
                raise ValueError(f"Chat API response returned no choices: {resp_json}")
            
            message = choices[0].get("message", {})
            images_list = message.get("images", [])
            
            if not images_list:
                # If no images, check if it returned text content
                content_text = message.get("content")
                if content_text:
                    raise ValueError(f"Model returned text instead of image: {content_text}")
                raise ValueError(f"Chat API response message contains no images: {resp_json}")
                
            for idx, item in enumerate(images_list):
                img_url = item.get("image_url", {}).get("url", "")
                if not img_url:
                    raise ValueError(f"Missing image_url in response item: {item}")
                
                try:
                    if img_url.startswith("data:image/"):
                        # Decode Base64 data URL
                        header, encoded = img_url.split(",", 1)
                        img_bytes = base64.b64decode(encoded)
                        output_pil_images.append(Image.open(io.BytesIO(img_bytes)))
                    elif img_url.startswith("http://") or img_url.startswith("https://"):
                        # Download from URL
                        with urllib.request.urlopen(img_url, timeout=60) as img_resp:
                            img_bytes = img_resp.read()
                        output_pil_images.append(Image.open(io.BytesIO(img_bytes)))
                    else:
                        raise ValueError(f"Unsupported image URL protocol: {img_url}")
                except Exception as e:
                    raise RuntimeError(f"Failed to decode image index {idx}: {e}")
        else:
            data_list = resp_json.get("data", [])
            if not data_list:
                raise ValueError(f"API response returned no image data: {resp_json}")

            for idx, item in enumerate(data_list):
                b64_json = item.get("b64_json")
                item_url = item.get("url")

                try:
                    if b64_json:
                        img_bytes = base64.b64decode(b64_json)
                        output_pil_images.append(Image.open(io.BytesIO(img_bytes)))
                    elif item_url:
                        # 从 URL 下载
                        with urllib.request.urlopen(item_url, timeout=60) as img_resp:
                            img_bytes = img_resp.read()
                        output_pil_images.append(Image.open(io.BytesIO(img_bytes)))
                    else:
                        raise KeyError("Missing both 'b64_json' and 'url' in image response item")
                except Exception as e:
                    raise RuntimeError(f"Failed to load image index {idx}: {e}")

        # 7. 转换为 ComfyUI Tensor 批次输出
        if not output_pil_images:
            raise RuntimeError("Failed to decode any images from the API response")

        return (pil_to_tensor_batch(output_pil_images),)
