"""
分镜检测核心模块
================
封装分镜检测、短镜头合并、视频切割、首帧提取四个纯函数，不依赖 ComfyUI。
"""

import json
import subprocess
from pathlib import Path
from typing import List, Tuple, Optional

import cv2
import numpy as np
import torch

from scenedetect import open_video, SceneManager
from scenedetect.detectors import ContentDetector, AdaptiveDetector, ThresholdDetector

DEFAULT_THRESHOLDS = {"content": 27.0, "adaptive": 3.0, "threshold": 12.0}


def _build_detector(name: str, threshold: float, min_scene_len: str):
    """构建 PySceneDetect 检测器实例。min_scene_len 直接传字符串如 '0.6s'。"""
    if name == "content":
        return ContentDetector(threshold=threshold, min_scene_len=min_scene_len)
    if name == "adaptive":
        return AdaptiveDetector(adaptive_threshold=threshold, min_scene_len=min_scene_len)
    if name == "threshold":
        return ThresholdDetector(threshold=threshold, min_scene_len=min_scene_len)
    raise ValueError(f"未知的检测器类型: {name}，可选值: content / adaptive / threshold")


def detect_scenes(
    video_path: str,
    detector: str = "adaptive",
    threshold: Optional[float] = None,
    min_scene_len_sec: float = 0.6,
    skip_first_frames: int = 0,
    frame_load_cap: int = 0,
) -> List[Tuple]:
    """
    检测视频中的镜头边界。

    Args:
        video_path: 视频文件路径
        detector: 检测器类型 ("content" / "adaptive" / "threshold")
        threshold: 检测灵敏度，None 则使用检测器默认值
        min_scene_len_sec: 最短镜头时长（秒）
        skip_first_frames: 跳过视频前X帧
        frame_load_cap: 帧读取上限（为0表示读取到视频结束）

    Returns:
        [(start_timecode, end_timecode), ...] 时间戳对列表
    """
    if threshold is None or threshold <= 0:
        threshold = DEFAULT_THRESHOLDS.get(detector, 3.0)

    video = open_video(video_path)
    
    if skip_first_frames > 0:
        video.seek(skip_first_frames)
        
    duration = None
    if frame_load_cap > 0:
        duration = frame_load_cap

    scene_manager = SceneManager()
    scene_manager.add_detector(
        _build_detector(detector, threshold, f"{min_scene_len_sec}s")
    )
    scene_manager.detect_scenes(video=video, show_progress=False, duration=duration)
    return scene_manager.get_scene_list()


def merge_short_scenes(
    scene_list: List[Tuple],
    min_duration_sec: float = 1.0,
) -> List[Tuple]:
    """
    二次后处理：将时长短于 min_duration_sec 的碎片镜头合并到前一个镜头。

    真实素材上检测几乎必然产生几帧到零点几秒的"毛刺"碎片，
    直接并入前一个镜头是无损处理方式。
    """
    if not scene_list:
        return scene_list

    merged = [list(scene_list[0])]
    for start, end in scene_list[1:]:
        cur_start, cur_end = merged[-1]
        duration = (cur_end - cur_start).get_seconds()
        if duration < min_duration_sec:
            merged[-1][1] = end  # 并入上一个
        else:
            merged.append([start, end])

    # 检查最后一段是否过短
    if len(merged) > 1:
        last_start, last_end = merged[-1]
        last_duration = (last_end - last_start).get_seconds()
        if last_duration < min_duration_sec:
            merged[-2][1] = merged[-1][1]
            merged.pop()

    return [tuple(x) for x in merged]


def split_video_to_files(
    video_path: str,
    scene_list: List[Tuple],
    output_dir: str,
    filename_prefix: str = "scene",
    fast_copy: bool = False,
    force_rate: float = 0.0,
    custom_width: int = 0,
    custom_height: int = 0,
    select_every_nth: int = 1,
) -> List[dict]:
    """
    按分镜列表将视频切割为多个独立文件，按顺序命名。

    Args:
        video_path: 原始视频路径
        scene_list: detect_scenes/merge_short_scenes 返回的时间戳对列表
        output_dir: 输出目录
        filename_prefix: 输出文件名前缀
        fast_copy: True=快速模式(-c copy)，False=精确模式(重编码)
        force_rate: 强制输出视频帧率（0=保持原样）
        custom_width: 目标宽度（0=保持原样）
        custom_height: 目标高度（0=保持原样）
        select_every_nth: 帧间隔采样（1=全帧，>1=跳帧采样）

    Returns:
        包含每个分镜元数据的列表
    """
    # 检查 ffmpeg 可用性
    try:
        subprocess.run(
            ["ffmpeg", "-version"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        raise RuntimeError(
            "未找到 ffmpeg，请安装 ffmpeg 并确保其在系统 PATH 中。\n"
            "下载地址: https://ffmpeg.org/download.html"
        )

    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    # 如果指定了任何分辨率、帧率或采样率修改，强制进入重编码模式（fast_copy 必须为 False）
    if force_rate > 0 or custom_width > 0 or custom_height > 0 or select_every_nth > 1:
        fast_copy = False

    manifest = []
    for i, (start, end) in enumerate(scene_list, start=1):
        out_file = out_path / f"{filename_prefix}_{i:03d}.mp4"
        start_sec = start.get_seconds()
        end_sec = end.get_seconds()
        duration_sec = end_sec - start_sec

        if fast_copy:
            cmd = [
                "ffmpeg", "-y",
                "-ss", str(start_sec),
                "-i", video_path,
                "-t", str(duration_sec),
                "-map", "0",
                "-c", "copy",
                str(out_file),
            ]
        else:
            # 构建视频滤镜
            vf_filters = []
            if select_every_nth > 1:
                vf_filters.append(f"select=not(mod(n\\,{select_every_nth}))")
            if custom_width > 0 or custom_height > 0:
                if custom_width > 0 and custom_height > 0:
                    vf_filters.append(f"scale={custom_width}:{custom_height}")
                elif custom_width > 0:
                    vf_filters.append(f"scale={custom_width}:-2")
                else:
                    vf_filters.append(f"scale=-2:{custom_height}")

            cmd = [
                "ffmpeg", "-y",
                "-ss", str(start_sec),
                "-i", video_path,
                "-t", str(duration_sec),
            ]
            
            # 指定轨道映射
            cmd.extend(["-map", "0:v:0", "-map", "0:a?", "-map", "0:s?"])

            if vf_filters:
                cmd.extend(["-vf", ",".join(vf_filters)])

            if force_rate > 0:
                cmd.extend(["-r", str(force_rate)])

            cmd.extend([
                "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
                "-c:a", "aac",
                str(out_file),
            ])

        subprocess.run(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            check=True,
        )

        manifest.append({
            "scene_number": i,
            "start_timecode": start.get_timecode(),
            "end_timecode": end.get_timecode(),
            "start_seconds": round(start_sec, 3),
            "end_seconds": round(end_sec, 3),
            "duration_seconds": round(duration_sec, 3),
            "file_path": str(out_file.resolve()),
        })

    return manifest


def get_scene_first_frames(
    video_path: str,
    scene_list: List[Tuple],
    custom_width: int = 0,
    custom_height: int = 0,
) -> torch.Tensor:
    """
    提取每个分镜的首帧图片，返回 [N, H, W, C] 的 float32 张量。

    使用 OpenCV seek 到每个分镜的 start_seconds，读取一帧并转换为 RGB。
    """
    if not scene_list:
        raise ValueError("scene_list 为空，无法提取首帧")

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise RuntimeError(f"OpenCV 无法打开视频: {video_path}")

    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    frames = []

    for start, _end in scene_list:
        start_sec = start.get_seconds()
        # 使用毫秒级 seek
        cap.set(cv2.CAP_PROP_POS_MSEC, start_sec * 1000.0)
        ok, frame = cap.read()
        if not ok:
            # 如果 seek 失败，尝试用帧号
            frame_no = int(start_sec * fps)
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_no)
            ok, frame = cap.read()
        if not ok:
            raise RuntimeError(f"无法读取视频帧 (时间: {start_sec:.3f}s)")

        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        frame = _resize_frame(frame, custom_width, custom_height)
        arr = frame.astype(np.float32) / 255.0
        frames.append(torch.from_numpy(arr))

    cap.release()

    if not frames:
        raise RuntimeError(f"未从视频中提取到任何首帧: {video_path}")

    return torch.stack(frames, dim=0)


def _resize_frame(frame: np.ndarray, custom_width: int, custom_height: int) -> np.ndarray:
    """等比缩放帧（与 video_utils 中同名函数逻辑一致）。"""
    h, w = frame.shape[:2]
    target_w = int(custom_width or 0)
    target_h = int(custom_height or 0)

    if target_w <= 0 and target_h <= 0:
        return frame
    if target_w > 0 and target_h <= 0:
        target_h = max(1, int(h * (target_w / w)))
    elif target_h > 0 and target_w <= 0:
        target_w = max(1, int(w * (target_h / h)))

    return cv2.resize(frame, (target_w, target_h), interpolation=cv2.INTER_AREA)
