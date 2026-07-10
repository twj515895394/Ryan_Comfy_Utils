import asyncio
import json as json_module

import folder_paths
from pathlib import Path
from server import PromptServer
from aiohttp import web

from ..core.scene_detect import (
    detect_scenes,
    merge_short_scenes,
    split_video_to_files,
    get_scene_first_frames,
)

from ..core.video_utils import (
    clamp_index,
    get_video_info,
    load_video_frames,
    sample_image_batch,
    save_image_batch,
    scan_video_files,
    sort_video_files,
    video_info_to_json,
)

# 注册安全的本地视频流式接口，以支持 ComfyUI 前端直接播放或预览视频
if hasattr(PromptServer, "instance") and PromptServer.instance:
    @PromptServer.instance.routes.get("/ryan_comfy_utils/view_video")
    async def ryan_view_video(request):
        video_path_str = request.query.get("path")
        if not video_path_str:
            return web.Response(status=400, text="Missing path parameter")

        path = Path(video_path_str).resolve()

        # 路径安全及格式校验
        allowed_exts = {".mp4", ".mov", ".mkv", ".webm", ".avi"}
        if path.suffix.lower() not in allowed_exts:
            return web.Response(status=403, text="Forbidden file type")

        if not path.exists() or not path.is_file():
            return web.Response(status=404, text="Video file not found")

        return web.FileResponse(path)

    @PromptServer.instance.routes.post("/ryan_comfy_utils/select_dir")
    async def ryan_select_dir(request):
        import asyncio

        def run_dialog():
            import tkinter as tk
            from tkinter import filedialog
            try:
                root = tk.Tk()
                root.withdraw()
                root.attributes("-topmost", True)
                directory = filedialog.askdirectory(title="选择视频文件夹")
                root.destroy()
                return directory
            except Exception as e:
                print(f"Error opening tkinter folder dialog: {e}")
                return ""

        selected = await asyncio.to_thread(run_dialog)
        return web.json_response({"dir": selected})

    @PromptServer.instance.routes.post("/ryan_comfy_utils/get_video_info")
    async def ryan_get_video_info_api(request):
        try:
            body = await request.json()
            video_dir = body.get("video_dir", "")
            index = int(body.get("index", 0))
            recursive = bool(body.get("recursive", False))
            extensions = body.get("extensions", "mp4,mov,mkv,webm,avi")
            sort_mode = body.get("sort_mode", "filename_asc")

            files = scan_video_files(video_dir, extensions, recursive)
            files = sort_video_files(files, sort_mode)
            total = len(files)
            if total == 0:
                return web.json_response({"error": "No videos found", "total": 0})

            actual_index = clamp_index(index, total)
            selected = files[actual_index]
            info = get_video_info(str(selected))
            info["total_files"] = total
            info["actual_index"] = actual_index
            return web.json_response(info)
        except Exception as e:
            return web.json_response({"error": str(e)}, status=500)

    @PromptServer.instance.routes.post("/ryan_comfy_utils/get_single_video_info")
    async def ryan_get_single_video_info(request):
        try:
            body = await request.json()
            video_path = body.get("video_path", "")
            if not video_path or not Path(video_path).exists():
                return web.json_response({"error": "Video path not found"}, status=404)
            info = get_video_info(video_path)
            return web.json_response(info)
        except Exception as e:
            return web.json_response({"error": str(e)}, status=500)

    @PromptServer.instance.routes.post("/ryan_comfy_utils/select_video_file")
    async def ryan_select_video_file(request):
        def run_dialog():
            import tkinter as tk
            from tkinter import filedialog
            try:
                root = tk.Tk()
                root.withdraw()
                root.attributes("-topmost", True)
                file_path = filedialog.askopenfilename(
                    title="选择视频文件",
                    filetypes=[
                        ("视频文件", "*.mp4 *.mov *.mkv *.avi *.webm"),
                        ("所有文件", "*.*"),
                    ],
                )
                root.destroy()
                return file_path or ""
            except Exception as e:
                print(f"Error opening tkinter file dialog: {e}")
                return ""

        selected = await asyncio.to_thread(run_dialog)
        return web.json_response({"path": selected})


_LAST_LOADED_VIDEO_PATH = None


class RyanBatchVideoLoader:
    @classmethod
    def INPUT_TYPES(cls):
        input_dir = folder_paths.get_input_directory()
        return {
            "required": {
                "video_dir": ("STRING", {"default": input_dir}),
                "index": ("INT", {"default": 0, "min": 0, "max": 999999, "step": 1}),
                "recursive": ("BOOLEAN", {"default": False}),
                "extensions": ("STRING", {"default": "mp4,mov,mkv,webm,avi"}),
                "sort_mode": (["filename_asc", "filename_desc", "natural_asc", "natural_desc", "mtime_asc", "mtime_desc"], {"default": "filename_asc"}),
                "backend_mode": (["auto", "opencv", "ffmpeg"], {"default": "auto"}),
                "force_rate": ("FLOAT", {"default": 0, "min": 0, "max": 120, "step": 1}),
                "custom_width": ("INT", {"default": 0, "min": 0, "max": 8192, "step": 8}),
                "custom_height": ("INT", {"default": 0, "min": 0, "max": 8192, "step": 8}),
                "frame_load_cap": ("INT", {"default": 0, "min": 0, "max": 100000, "step": 1}),
                "skip_first_frames": ("INT", {"default": 0, "min": 0, "max": 100000, "step": 1}),
                "select_every_nth": ("INT", {"default": 1, "min": 1, "max": 100000, "step": 1}),
            }
        }

    RETURN_TYPES = ("IMAGE", "INT", "STRING", "STRING", "INT", "INT", "STRING", "STRING")
    RETURN_NAMES = ("images", "frame_count", "video_path", "filename", "index", "total", "file_list_text", "video_info_json")
    FUNCTION = "load"
    CATEGORY = "Ryan Utils / Video"

    def load(self, video_dir, index, recursive, extensions, sort_mode, backend_mode, force_rate, custom_width, custom_height, frame_load_cap, skip_first_frames, select_every_nth):
        files = scan_video_files(video_dir, extensions, recursive)
        files = sort_video_files(files, sort_mode)
        total = len(files)
        if total == 0:
            raise FileNotFoundError(f"No video files found in: {video_dir}")

        actual_index = clamp_index(index, total)
        selected = files[actual_index]

        global _LAST_LOADED_VIDEO_PATH
        _LAST_LOADED_VIDEO_PATH = str(selected.resolve())

        images, frame_count = load_video_frames(
            str(selected),
            backend_mode=backend_mode,
            force_rate=force_rate,
            custom_width=custom_width,
            custom_height=custom_height,
            frame_load_cap=frame_load_cap,
            skip_first_frames=skip_first_frames,
            select_every_nth=select_every_nth,
        )
        file_list_text = "\n".join(f"{i}: {p.name}" for i, p in enumerate(files))
        video_info_json = video_info_to_json(
            str(selected),
            extra={
                "selected_index": actual_index,
                "total_files": total,
                "decoded_frame_count": frame_count,
                "backend_mode": backend_mode,
                "force_rate": force_rate,
                "custom_width": custom_width,
                "custom_height": custom_height,
                "frame_load_cap": frame_load_cap,
                "skip_first_frames": skip_first_frames,
                "select_every_nth": select_every_nth,
            },
        )
        return {
            "ui": {"video": [str(selected.resolve())]},
            "result": (images, frame_count, str(selected), selected.name, actual_index, total, file_list_text, video_info_json)
        }

    @classmethod
    def IS_CHANGED(cls, video_dir, index, recursive, extensions, sort_mode, backend_mode, force_rate, custom_width, custom_height, frame_load_cap, skip_first_frames, select_every_nth):
        files = sort_video_files(scan_video_files(video_dir, extensions, recursive), sort_mode)
        total = len(files)
        if total == 0:
            return f"empty:{video_dir}"
        actual_index = clamp_index(index, total)
        selected = files[actual_index]
        return f"{selected}:{selected.stat().st_mtime}:{index}:{sort_mode}:{force_rate}:{custom_width}:{custom_height}:{frame_load_cap}:{skip_first_frames}:{select_every_nth}:{backend_mode}"


SAMPLE_MODE_MAP = {
    "首尾与均匀采样": "head_tail",
    "完全均匀采样": "uniform",
    "固定间隔采样": "interval",
    "自定义帧索引": "custom_indexes",
    "分镜首帧采样": "scene_first_frame",
}

SAVE_MODE_MAP = {
    "仅预览不保存": "preview_only",
    "保存至 output 目录": "save_to_output",
}


class RyanVideoFrameSampler:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "sample_mode": (["首尾与均匀采样", "完全均匀采样", "固定间隔采样", "自定义帧索引", "分镜首帧采样"], {"default": "首尾与均匀采样"}),
                "frame_count": ("INT", {"default": 2, "min": 1, "max": 10, "step": 1}),
                "frame_interval": ("INT", {"default": 1, "min": 1, "max": 100000, "step": 1}),
                "custom_indexes": ("STRING", {"default": "0,-1"}),
                "save_mode": (["仅预览不保存", "保存至 output 目录"], {"default": "仅预览不保存"}),
                "output_subdir": ("STRING", {"default": "ryan_video_frames"}),
                "filename_prefix": ("STRING", {"default": "video_frame"}),
            },
            "optional": {
                "images": ("IMAGE",),
                "video_path": ("STRING", {"default": ""}),
                "scene_detector": (["自适应检测", "内容突变检测", "亮度阈值检测"], {"default": "自适应检测"}),
                "scene_threshold": ("FLOAT", {"default": 0.0, "min": 0.0, "max": 100.0, "step": 0.5}),
                "scene_min_len": ("FLOAT", {"default": 0.6, "min": 0.1, "max": 10.0, "step": 0.1}),
                "scene_merge_min": ("FLOAT", {"default": 1.0, "min": 0.0, "max": 10.0, "step": 0.1}),
            }
        }

    RETURN_TYPES = ("IMAGE", "STRING", "INT", "STRING")
    RETURN_NAMES = ("images", "frame_indexes", "frame_count", "saved_paths_text")
    FUNCTION = "sample"
    CATEGORY = "Ryan Utils / Video"

    def sample(self, sample_mode, frame_count, frame_interval, custom_indexes, save_mode, output_subdir, filename_prefix, 
               images=None, video_path="", scene_detector="自适应检测", scene_threshold=0.0, scene_min_len=0.6, scene_merge_min=1.0):
        real_sample_mode = SAMPLE_MODE_MAP.get(sample_mode, "head_tail")
        real_save_mode = SAVE_MODE_MAP.get(save_mode, "preview_only")
        
        if real_sample_mode == "scene_first_frame":
            # If video_path is empty or missing, fallback to the last successfully loaded video path
            if not video_path:
                global _LAST_LOADED_VIDEO_PATH
                if _LAST_LOADED_VIDEO_PATH and Path(_LAST_LOADED_VIDEO_PATH).exists():
                    video_path = _LAST_LOADED_VIDEO_PATH

            if not video_path or not Path(video_path).exists():
                raise FileNotFoundError(
                    f"分镜采样模式需要有效的视频文件路径。请将视频加载器（如 Ryan Batch Video Loader）的 video_path 输出连接到采样器的 video_path 输入，或者确保视频加载器已成功运行过。当前路径不存在或为空: {video_path}"
                )
            
            real_detector = DETECTOR_MAP.get(scene_detector, "adaptive")
            real_threshold = scene_threshold if scene_threshold > 0 else None
            
            scene_list = detect_scenes(
                video_path=video_path,
                detector=real_detector,
                threshold=real_threshold,
                min_scene_len_sec=scene_min_len,
            )
            scene_list = merge_short_scenes(scene_list, min_duration_sec=scene_merge_min)
            
            if not scene_list:
                raise ValueError("未检测到任何分镜，无法进行分镜首帧采样")
                
            sampled = get_scene_first_frames(video_path, scene_list)
            
            try:
                info = get_video_info(video_path)
                fps = info.get("fps", 25.0) or 25.0
            except Exception:
                fps = 25.0
                
            indexes = [int(start.get_seconds() * fps) for start, _ in scene_list]
        else:
            if images is None:
                raise ValueError("images input is required for standard sample modes")
            sampled, indexes = sample_image_batch(images, real_sample_mode, frame_count, frame_interval, custom_indexes)
            
        saved_paths = []
        if real_save_mode == "save_to_output":
            output_dir = folder_paths.get_output_directory()
            saved_paths = save_image_batch(sampled, output_dir, output_subdir, filename_prefix)
        return (sampled, ",".join(str(i) for i in indexes), sampled.shape[0], "\n".join(saved_paths))


class RyanImageBatchSplitter:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "images": ("IMAGE",),
                "output_count": ("INT", {"default": 4, "min": 1, "max": 12, "step": 1}),
            }
        }

    RETURN_TYPES = ("IMAGE",) * 12
    RETURN_NAMES = tuple(f"image_{i:02d}" for i in range(1, 13))
    FUNCTION = "run"
    CATEGORY = "Ryan Utils / Image"

    def run(self, images, output_count):
        import uuid
        import numpy as np
        from PIL import Image
        
        if images is None:
            return {
                "ui": {"images": []},
                "result": (None,) * 12
            }

        batch_size = images.shape[0]
        temp_dir = folder_paths.get_temp_directory()
        prefix = f"ryan_split_{uuid.uuid4().hex}"
        
        saved_images_ui = []
        output_images = []
        
        for i in range(12):
            if i < batch_size:
                img_tensor = images[i]
                output_images.append(img_tensor.unsqueeze(0))
                
                # Save preview image
                img_np = (img_tensor.cpu().numpy() * 255.0).clip(0, 255).astype(np.uint8)
                pil_img = Image.fromarray(img_np)
                filename = f"{prefix}_{i:02d}.png"
                filepath = Path(temp_dir) / filename
                pil_img.save(filepath, format="PNG")
                
                saved_images_ui.append({
                    "filename": filename,
                    "subfolder": "",
                    "type": "temp"
                })
            else:
                output_images.append(None)
                
        return {
            "ui": {"images": saved_images_ui},
            "result": tuple(output_images)
        }


DETECTOR_MAP = {
    "自适应检测": "adaptive",
    "内容突变检测": "content",
    "亮度阈值检测": "threshold",
}


class RyanVideoSceneSplitter:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "video_path": ("STRING", {"default": ""}),
                "output_dir": ("STRING", {"default": "scene_splits"}),
                "filename_prefix": ("STRING", {"default": "scene"}),
                "detector": (["自适应检测", "内容突变检测", "亮度阈值检测"], {"default": "自适应检测"}),
                "threshold": ("FLOAT", {"default": 0.0, "min": 0.0, "max": 100.0, "step": 0.5}),
                "min_scene_len": ("FLOAT", {"default": 0.6, "min": 0.1, "max": 10.0, "step": 0.1}),
                "merge_min_duration": ("FLOAT", {"default": 1.0, "min": 0.0, "max": 10.0, "step": 0.1}),
                "fast_copy": ("BOOLEAN", {"default": False}),
                "force_rate": ("FLOAT", {"default": 0.0, "min": 0.0, "max": 120.0, "step": 0.1}),
                "custom_width": ("INT", {"default": 0, "min": 0, "max": 8192, "step": 8}),
                "custom_height": ("INT", {"default": 0, "min": 0, "max": 8192, "step": 8}),
                "frame_load_cap": ("INT", {"default": 0, "min": 0, "max": 1000000, "step": 1}),
                "skip_first_frames": ("INT", {"default": 0, "min": 0, "max": 1000000, "step": 1}),
                "select_every_nth": ("INT", {"default": 1, "min": 1, "max": 100, "step": 1}),
            }
        }

    RETURN_TYPES = ("INT", "STRING", "STRING")
    RETURN_NAMES = ("scene_count", "manifest_json", "output_dir")
    FUNCTION = "run"
    CATEGORY = "Ryan Utils / Video"

    def run(self, video_path, output_dir, filename_prefix, detector, threshold, min_scene_len, merge_min_duration, fast_copy,
            force_rate=0.0, custom_width=0, custom_height=0, frame_load_cap=0, skip_first_frames=0, select_every_nth=1):
        # Sanitize parameters against None / invalid string inputs passed by older workflows or API clients
        try:
            force_rate = float(force_rate) if force_rate is not None else 0.0
        except Exception:
            force_rate = 0.0

        try:
            custom_width = int(custom_width) if custom_width is not None else 0
        except Exception:
            custom_width = 0

        try:
            custom_height = int(custom_height) if custom_height is not None else 0
        except Exception:
            custom_height = 0

        try:
            frame_load_cap = int(frame_load_cap) if frame_load_cap is not None else 0
        except Exception:
            frame_load_cap = 0

        try:
            skip_first_frames = int(skip_first_frames) if skip_first_frames is not None else 0
        except Exception:
            skip_first_frames = 0

        try:
            select_every_nth = int(select_every_nth) if select_every_nth is not None else 1
        except Exception:
            select_every_nth = 1

        if not video_path or not Path(video_path).exists():
            raise FileNotFoundError(f"视频文件不存在: {video_path}")

        # Save to global cache for video frame sampler fallback
        global _LAST_LOADED_VIDEO_PATH
        _LAST_LOADED_VIDEO_PATH = str(Path(video_path).resolve())

        real_detector = DETECTOR_MAP.get(detector, "adaptive")
        real_threshold = threshold if threshold > 0 else None

        scene_list = detect_scenes(
            video_path=video_path,
            detector=real_detector,
            threshold=real_threshold,
            min_scene_len_sec=min_scene_len,
            skip_first_frames=skip_first_frames,
            frame_load_cap=frame_load_cap,
        )

        scene_list = merge_short_scenes(scene_list, min_duration_sec=merge_min_duration)

        if not scene_list:
            return (0, "[]", output_dir)

        abs_output_dir = str(Path(folder_paths.get_output_directory()) / output_dir)

        manifest = split_video_to_files(
            video_path=video_path,
            scene_list=scene_list,
            output_dir=abs_output_dir,
            filename_prefix=filename_prefix,
            fast_copy=fast_copy,
            force_rate=force_rate,
            custom_width=custom_width,
            custom_height=custom_height,
            select_every_nth=select_every_nth,
        )

        manifest_json = json_module.dumps(manifest, ensure_ascii=False, indent=2)

        return (len(manifest), manifest_json, abs_output_dir)
