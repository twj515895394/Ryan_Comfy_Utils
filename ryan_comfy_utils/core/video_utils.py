import os
import subprocess
from pathlib import Path
from typing import List, Tuple

import cv2
import numpy as np
import torch
from PIL import Image


def scan_video_files(video_dir: str, extensions: str, recursive: bool = False) -> List[Path]:
    root = Path(video_dir).expanduser()
    if not root.exists() or not root.is_dir():
        raise FileNotFoundError(f"Invalid video_dir: {video_dir}")

    ext_set = {e.strip().lower().lstrip(".") for e in extensions.split(",") if e.strip()}
    pattern_iter = root.rglob("*") if recursive else root.glob("*")
    files = [p for p in pattern_iter if p.is_file() and p.suffix.lower().lstrip(".") in ext_set]
    return files


def sort_video_files(files: List[Path], sort_mode: str = "filename_asc") -> List[Path]:
    mode = sort_mode or "filename_asc"
    reverse = mode.endswith("desc")

    if mode.startswith("mtime"):
        return sorted(files, key=lambda p: p.stat().st_mtime, reverse=reverse)
    return sorted(files, key=lambda p: p.name.lower(), reverse=reverse)


def clamp_index(index: int, total: int) -> int:
    if total <= 0:
        return 0
    return max(0, min(int(index or 0), total - 1))


def _resize_frame(frame: np.ndarray, custom_width: int, custom_height: int) -> np.ndarray:
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


def load_video_frames_opencv(
    video_path: str,
    force_rate: float = 0,
    custom_width: int = 0,
    custom_height: int = 0,
    frame_load_cap: int = 0,
    skip_first_frames: int = 0,
    select_every_nth: int = 1,
) -> Tuple[torch.Tensor, int]:
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise RuntimeError(f"OpenCV failed to open video: {video_path}")

    fps = cap.get(cv2.CAP_PROP_FPS) or 0
    source_step = 1
    if force_rate and force_rate > 0 and fps > 0:
        source_step = max(1, round(fps / float(force_rate)))

    select_every_nth = max(1, int(select_every_nth or 1))
    effective_step = max(1, source_step * select_every_nth)
    skip_first_frames = max(0, int(skip_first_frames or 0))
    frame_load_cap = max(0, int(frame_load_cap or 0))

    frames = []
    frame_idx = -1
    selected = 0

    while True:
        ok, frame = cap.read()
        if not ok:
            break
        frame_idx += 1
        if frame_idx < skip_first_frames:
            continue
        if (frame_idx - skip_first_frames) % effective_step != 0:
            continue

        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        frame = _resize_frame(frame, custom_width, custom_height)
        arr = frame.astype(np.float32) / 255.0
        frames.append(torch.from_numpy(arr))
        selected += 1
        if frame_load_cap > 0 and selected >= frame_load_cap:
            break

    cap.release()

    if not frames:
        raise RuntimeError(f"No frames decoded from video: {video_path}")

    return torch.stack(frames, dim=0), len(frames)


def load_video_frames_ffmpeg(
    video_path: str,
    force_rate: float = 0,
    custom_width: int = 0,
    custom_height: int = 0,
    frame_load_cap: int = 0,
    skip_first_frames: int = 0,
    select_every_nth: int = 1,
) -> Tuple[torch.Tensor, int]:
    # Lightweight FFmpeg fallback: decode by asking OpenCV to use the file after ffmpeg validation.
    # This keeps v0.1 stable while preserving the public backend option.
    subprocess.run(["ffmpeg", "-v", "error", "-i", video_path, "-f", "null", "-"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    return load_video_frames_opencv(
        video_path,
        force_rate=force_rate,
        custom_width=custom_width,
        custom_height=custom_height,
        frame_load_cap=frame_load_cap,
        skip_first_frames=skip_first_frames,
        select_every_nth=select_every_nth,
    )


def load_video_frames(video_path: str, backend_mode: str = "auto", **kwargs) -> Tuple[torch.Tensor, int]:
    mode = (backend_mode or "auto").lower()
    if mode == "opencv":
        return load_video_frames_opencv(video_path, **kwargs)
    if mode == "ffmpeg":
        return load_video_frames_ffmpeg(video_path, **kwargs)

    try:
        return load_video_frames_opencv(video_path, **kwargs)
    except Exception:
        return load_video_frames_ffmpeg(video_path, **kwargs)


def sample_image_batch(images: torch.Tensor, sample_mode: str, frame_count: int, frame_interval: int = 1):
    if images is None or not isinstance(images, torch.Tensor):
        raise ValueError("images input is required")
    if images.ndim == 3:
        images = images.unsqueeze(0)
    total = images.shape[0]
    if total <= 0:
        raise ValueError("images batch is empty")

    count = max(1, min(int(frame_count or 2), 10))
    mode = sample_mode or "head_tail"

    if mode == "head_tail":
        indexes = [0] if total == 1 or count == 1 else [0, total - 1]
        if count > 2 and total > 2:
            middle_count = count - 2
            mids = np.linspace(1, total - 2, middle_count).round().astype(int).tolist()
            indexes = [0] + mids + [total - 1]
    elif mode == "interval":
        step = max(1, int(frame_interval or 1))
        indexes = list(range(0, total, step))[:count]
    else:
        indexes = np.linspace(0, total - 1, count).round().astype(int).tolist()

    indexes = sorted(dict.fromkeys(max(0, min(i, total - 1)) for i in indexes))[:10]
    return images[indexes], indexes


def save_image_batch(images: torch.Tensor, output_dir: str, subdir: str, filename_prefix: str) -> int:
    folder = Path(output_dir) / (subdir or "ryan_video_frames")
    folder.mkdir(parents=True, exist_ok=True)
    prefix = filename_prefix or "video_frame"

    saved = 0
    for i, img in enumerate(images):
        arr = img.detach().cpu().numpy()
        arr = np.clip(arr * 255.0, 0, 255).astype(np.uint8)
        Image.fromarray(arr).save(folder / f"{prefix}_{i:03d}.png")
        saved += 1
    return saved
