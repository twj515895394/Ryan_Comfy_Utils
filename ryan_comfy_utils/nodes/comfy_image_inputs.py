"""ComfyUI 多图输入约定：最多 10 个 IMAGE 槽位 image_01 … image_10。"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ..acp.image_slot_paths import session_input_images_dir

MAX_RYAN_IMAGE_SLOTS = 10
IMAGE_SLOT_PREFIX = "image_"


def image_slot_name(index: int) -> str:
    if index < 1 or index > MAX_RYAN_IMAGE_SLOTS:
        raise ValueError(f"image slot index must be 1..{MAX_RYAN_IMAGE_SLOTS}")
    return f"{IMAGE_SLOT_PREFIX}{index:02d}"


def build_image_slot_input_types(
    *,
    include_paths: bool = False,
    default_slot_count: int = 1,
) -> dict[str, tuple]:
    """默认仅暴露 image_01；其余槽位由前端「+」动态添加。"""
    optional: dict[str, tuple] = {
        image_slot_name(1): ("IMAGE",),
        "image_slot_count": (
            "INT",
            {"default": default_slot_count, "min": 1, "max": MAX_RYAN_IMAGE_SLOTS, "step": 1},
        ),
    }
    for i in range(2, MAX_RYAN_IMAGE_SLOTS + 1):
        optional[image_slot_name(i)] = ("IMAGE",)
    if include_paths:
        optional["image_paths"] = ("STRING", {"default": "", "multiline": True})
    return optional


def collect_image_tensors_from_kwargs(
    kwargs: dict[str, Any],
    *,
    max_slots: int | None = None,
) -> list[Any]:
    """按槽位顺序收集已连接的 IMAGE tensor（None 表示未连接）。"""
    limit = max_slots or MAX_RYAN_IMAGE_SLOTS
    slots = []
    for i in range(1, limit + 1):
        slots.append(kwargs.get(image_slot_name(i)))
    return slots


def count_connected_image_slots(slots: list[Any]) -> int:
    return sum(1 for s in slots if s is not None)


def trim_trailing_empty_slots(slots: list[Any]) -> list[Any]:
    trimmed = list(slots)
    while trimmed and trimmed[-1] is None:
        trimmed.pop()
    return trimmed


def materialize_image_slots_to_directory(
    target_dir: Path,
    slots: list[Any],
    *,
    prefix: str = "ryan",
) -> list[str]:
    """将各槽位 tensor 落盘为 PNG，返回绝对路径列表。"""
    from ..core.image_utils import tensor_batch_to_pil

    target_dir.mkdir(parents=True, exist_ok=True)
    paths: list[str] = []
    for slot_index, tensor in enumerate(slots, start=1):
        if tensor is None:
            continue
        for frame_index, pil_img in enumerate(tensor_batch_to_pil(tensor)):
            filename = f"{prefix}_slot{slot_index:02d}_{frame_index:02d}.png"
            path = target_dir / filename
            pil_img.save(path, format="PNG")
            paths.append(str(path.resolve()))
    return paths


def flatten_slot_tensors_to_pil(slots: list[Any], *, max_total: int = 10) -> list:
    """按槽位顺序展开为 PIL，总数不超过 max_total。"""
    from ..core.image_utils import tensor_batch_to_pil

    pil_images = []
    for tensor in slots:
        if tensor is None:
            continue
        for pil_img in tensor_batch_to_pil(tensor):
            if len(pil_images) >= max_total:
                return pil_images
            pil_images.append(pil_img)
    return pil_images


def slots_from_explicit_args(image_slot_count, **slot_values) -> list[Any]:
    kwargs = {"image_slot_count": image_slot_count}
    for i in range(1, MAX_RYAN_IMAGE_SLOTS + 1):
        name = image_slot_name(i)
        if name in slot_values:
            kwargs[name] = slot_values[name]
    return collect_image_tensors_from_kwargs(
        kwargs, max_slots=int(image_slot_count or MAX_RYAN_IMAGE_SLOTS)
    )


def resolve_image_inputs_for_acp(
    *,
    workspace_root: Path | None = None,
    session_id: str = "",
    session_dir: Path | None = None,
    image_paths_text: str,
    image_slots: list[Any],
    parse_paths,
) -> list[str]:
    """合并多行路径与 IMAGE 槽位落盘路径，供 execute_text_session 使用。

    优先使用已准备好的 session_dir；否则用 workspace_root+session_id 推导。
    槽位直接写入 session_dir/input/images，避免额外 staging 目录。
    """
    paths = list(parse_paths(image_paths_text))
    connected = trim_trailing_empty_slots(image_slots)
    if not connected:
        return paths

    if session_dir is None:
        if workspace_root is None or not session_id:
            raise ValueError("session_dir or (workspace_root + session_id) required for image slots")
        from ..acp.workspace import prepare_workspace

        session_dir = prepare_workspace(workspace_root, session_id)

    target = session_input_images_dir(session_dir)
    paths.extend(materialize_image_slots_to_directory(target, connected))
    return paths
