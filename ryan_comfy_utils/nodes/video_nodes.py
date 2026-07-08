import os
from pathlib import Path

import folder_paths

from ..core.video_utils import (
    clamp_index,
    load_video_frames,
    sample_image_batch,
    save_image_batch,
    scan_video_files,
    sort_video_files,
)


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
                "sort_mode": (["filename_asc", "filename_desc", "mtime_asc", "mtime_desc"], {"default": "filename_asc"}),
                "backend_mode": (["auto", "opencv", "ffmpeg"], {"default": "auto"}),
                "force_rate": ("FLOAT", {"default": 0, "min": 0, "max": 120, "step": 1}),
                "custom_width": ("INT", {"default": 0, "min": 0, "max": 8192, "step": 8}),
                "custom_height": ("INT", {"default": 0, "min": 0, "max": 8192, "step": 8}),
                "frame_load_cap": ("INT", {"default": 0, "min": 0, "max": 100000, "step": 1}),
                "skip_first_frames": ("INT", {"default": 0, "min": 0, "max": 100000, "step": 1}),
                "select_every_nth": ("INT", {"default": 1, "min": 1, "max": 100000, "step": 1}),
            }
        }

    RETURN_TYPES = ("IMAGE", "INT", "STRING", "STRING", "INT", "INT", "STRING")
    RETURN_NAMES = ("images", "frame_count", "video_path", "filename", "index", "total", "file_list_text")
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
        return (images, frame_count, str(selected), selected.name, actual_index, total, file_list_text)

    @classmethod
    def IS_CHANGED(cls, video_dir, index, recursive, extensions, sort_mode, backend_mode, force_rate, custom_width, custom_height, frame_load_cap, skip_first_frames, select_every_nth):
        files = sort_video_files(scan_video_files(video_dir, extensions, recursive), sort_mode)
        total = len(files)
        if total == 0:
            return f"empty:{video_dir}"
        actual_index = clamp_index(index, total)
        selected = files[actual_index]
        return f"{selected}:{selected.stat().st_mtime}:{index}:{force_rate}:{custom_width}:{custom_height}:{frame_load_cap}:{skip_first_frames}:{select_every_nth}:{backend_mode}"


class RyanVideoFrameSampler:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "sample_mode": (["head_tail", "uniform", "interval"], {"default": "head_tail"}),
                "frame_count": ("INT", {"default": 2, "min": 1, "max": 10, "step": 1}),
                "frame_interval": ("INT", {"default": 1, "min": 1, "max": 100000, "step": 1}),
                "save_mode": (["preview_only", "save_to_output"], {"default": "preview_only"}),
                "output_subdir": ("STRING", {"default": "ryan_video_frames"}),
                "filename_prefix": ("STRING", {"default": "video_frame"}),
            },
            "optional": {
                "images": ("IMAGE",),
            }
        }

    RETURN_TYPES = ("IMAGE", "STRING", "INT")
    RETURN_NAMES = ("images", "frame_indexes", "frame_count")
    FUNCTION = "sample"
    CATEGORY = "Ryan Utils / Video"

    def sample(self, sample_mode, frame_count, frame_interval, save_mode, output_subdir, filename_prefix, images=None):
        sampled, indexes = sample_image_batch(images, sample_mode, frame_count, frame_interval)
        if save_mode == "save_to_output":
            output_dir = folder_paths.get_output_directory()
            save_image_batch(sampled, output_dir, output_subdir, filename_prefix)
        return (sampled, ",".join(str(i) for i in indexes), sampled.shape[0])
