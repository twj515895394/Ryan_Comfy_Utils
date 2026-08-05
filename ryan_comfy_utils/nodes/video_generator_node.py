import base64
import io
import json
import time
import urllib.request
import urllib.error
import uuid
from pathlib import Path
from PIL import Image
import torch

import folder_paths
from ..core.config_loader import list_profile_names, resolve_profile
from ..core.image_utils import pil_to_data_url, tensor_batch_to_pil, pil_to_tensor_batch
from ..core.video_utils import load_video_frames
from .comfy_image_inputs import build_image_slot_input_types, slots_from_explicit_args


def _profiles():
    try:
        return list_profile_names("image")
    except Exception:
        return ["default"]


class RyanVideoGenerator:
    @classmethod
    def INPUT_TYPES(cls):
        profiles = _profiles()
        return {
            "required": {
                "profile": (profiles,),
                "model_override": ("STRING", {"default": ""}),
                "prompt": ("STRING", {"default": "", "multiline": True}),
                "aspect_ratio": (["16:9", "9:16", "1:1", "4:3", "3:4", "3:2", "2:3"], {"default": "16:9"}),
                "resolution": (["480p", "720p"], {"default": "720p"}),
                "duration": ("INT", {"default": 5, "min": 1, "max": 15, "step": 1}),
                "polling_interval": ("INT", {"default": 5, "min": 1, "max": 60, "step": 1}),
                "extra_body_json": ("STRING", {"default": "", "multiline": True}),
            },
            "optional": build_image_slot_input_types(include_paths=False),
        }

    RETURN_TYPES = ("IMAGE", "STRING")
    RETURN_NAMES = ("images", "video_path")
    FUNCTION = "generate"
    CATEGORY = "Ryan Utils / Video"
    DESCRIPTION = "视频生成与编辑节点。支持异步通过 Grok-imagine-video 接口生成视频，支持文本生成视频、首帧生视频及多参考图生视频（Reference-to-Video）。"

    def generate(
        self,
        profile: str,
        model_override: str,
        prompt: str,
        aspect_ratio: str,
        resolution: str,
        duration: int,
        polling_interval: int,
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

        # 2. 收集图片输入
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
        
        pil_images = []
        for slot in slots:
            if slot is not None:
                pil_images.extend(tensor_batch_to_pil(slot))
        pil_images = pil_images[:5]

        # 3. 构造请求 Payload
        payload = {
            "model": model,
            "prompt": prompt,
            "aspect_ratio": aspect_ratio,
            "resolution": resolution,
            "duration": int(duration),
        }
        
        if len(pil_images) == 1:
            # Image-to-video mode (单图首帧)
            data_url = pil_to_data_url(pil_images[0], image_format="jpeg")
            payload["image"] = {"url": data_url}
        elif len(pil_images) > 1:
            # Reference-to-video mode (多参考图)
            ref_urls = []
            for img in pil_images:
                data_url = pil_to_data_url(img, image_format="jpeg")
                ref_urls.append({"url": data_url})
            payload["reference_image_urls"] = ref_urls

        # 合并自定义的额外参数
        if extra_body_json and extra_body_json.strip():
            try:
                extra_params = json.loads(extra_body_json)
                if isinstance(extra_params, dict):
                    payload.update(extra_params)
            except Exception as e:
                raise ValueError(f"Failed to parse extra_body_json: {e}")

        # 4. 发送异步生成任务
        submit_url = f"{base_url}/videos/generations"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        
        req = urllib.request.Request(
            submit_url,
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        
        submit_timeout = int(profile_data.get("timeout_seconds", 300))
        try:
            with urllib.request.urlopen(req, timeout=submit_timeout) as resp:
                resp_data = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as he:
            err_msg = he.read().decode("utf-8")
            raise RuntimeError(f"Video task submission failed with HTTP {he.code}: {err_msg}")
        except Exception as exc:
            raise RuntimeError(f"Video task submission failed: {exc}")
            
        request_id = resp_data.get("request_id")
        if not request_id:
            raise RuntimeError(f"Failed to obtain request_id from submission response: {resp_data}")
            
        print(f"[RyanVideoGenerator] Video generation task submitted successfully. Request ID: {request_id}")

        # 5. 循环轮询任务状态
        poll_url = f"{base_url}/videos/{request_id}"
        poll_headers = {
            "Authorization": f"Bearer {api_key}",
        }
        
        status = "pending"
        video_url = ""
        poll_req = urllib.request.Request(poll_url, headers=poll_headers, method="GET")
        
        max_attempts = 120
        attempts = 0
        
        while status == "pending" and attempts < max_attempts:
            time.sleep(max(1, int(polling_interval)))
            attempts += 1
            
            try:
                with urllib.request.urlopen(poll_req, timeout=60) as resp:
                    poll_data = json.loads(resp.read().decode("utf-8"))
            except urllib.error.HTTPError as he:
                err_msg = he.read().decode("utf-8")
                raise RuntimeError(f"Polling HTTP Error {he.code}: {err_msg}")
            except Exception as exc:
                print(f"[RyanVideoGenerator] Polling failed (attempt {attempts}): {exc}. Retrying...")
                continue
                
            status = poll_data.get("status", "pending")
            progress = poll_data.get("progress", 0)
            print(f"Polling status (attempt {attempts}): {status}, progress: {progress}%")
            
            if status == "done":
                video_obj = poll_data.get("video", {})
                video_url = video_obj.get("url")
                if not video_url:
                    raise RuntimeError(f"Task completed but missing video URL: {poll_data}")
                break
            elif status in ("failed", "expired"):
                err = poll_data.get("error", "Unknown error")
                raise RuntimeError(f"Video generation task {status}: {err}")
                
        if status == "pending":
            raise RuntimeError(f"Video generation task timed out after {attempts} attempts")

        # 6. 下载视频文件
        output_dir = Path(folder_paths.get_output_directory())
        output_dir.mkdir(parents=True, exist_ok=True)
        local_filename = f"ryan_grok_video_{uuid.uuid4().hex}.mp4"
        local_filepath = output_dir / local_filename
        
        print(f"[RyanVideoGenerator] Downloading generated video from {video_url} to {local_filepath}...")
        try:
            with urllib.request.urlopen(video_url, timeout=120) as video_resp:
                video_bytes = video_resp.read()
            with open(local_filepath, "wb") as f:
                f.write(video_bytes)
        except Exception as exc:
            raise RuntimeError(f"Failed to download video file: {exc}")

        # 7. 解码视频帧
        print(f"[RyanVideoGenerator] Decoding video frames from {local_filepath}...")
        try:
            images, frame_count = load_video_frames(
                str(local_filepath),
                backend_mode="auto",
            )
        except Exception as exc:
            raise RuntimeError(f"Failed to decode video file into frames: {exc}")
            
        return {
            "ui": {"video": [str(local_filepath.resolve())]},
            "result": (images, str(local_filepath.resolve())),
        }
