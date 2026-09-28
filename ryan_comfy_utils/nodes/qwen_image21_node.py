"""Ryan Qwen Image 2.1 conditioning and latent node."""

from __future__ import annotations

import math
from typing import Any

import torch


ASPECT_RATIOS: dict[str, tuple[int, int]] = {
    "1:1 (Square)": (1, 1),
    "2:3 (Portrait Photo)": (2, 3),
    "3:2 (Photo)": (3, 2),
    "3:4 (Portrait Standard)": (3, 4),
    "4:3 (Standard)": (4, 3),
    "9:16 (Portrait Widescreen)": (9, 16),
    "16:9 (Widescreen)": (16, 9),
    "21:9 (Ultrawide)": (21, 9),
}

MAX_IMAGE_SLOTS = 16
MIN_QWEN_SIZE = 16
MAX_QWEN_SIZE = 4096
QWEN_LATENT_MULTIPLE = 16
QWEN_REFERENCE_MULTIPLE = 32


def _round_to_multiple(value: float, multiple: int) -> int:
    return int(round(float(value) / multiple) * multiple)


def _clamp_qwen_size(value: int) -> int:
    return max(MIN_QWEN_SIZE, min(MAX_QWEN_SIZE, int(value)))


def normalize_custom_resolution(width: int, height: int) -> tuple[int, int]:
    """Normalize custom dimensions to the safe Qwen latent grid."""

    try:
        width_value = float(width)
        height_value = float(height)
    except (TypeError, ValueError) as exc:
        raise ValueError("width and height must be numeric") from exc

    if not math.isfinite(width_value) or not math.isfinite(height_value):
        raise ValueError("width and height must be finite")

    normalized_width = _clamp_qwen_size(
        _round_to_multiple(width_value, QWEN_LATENT_MULTIPLE)
    )
    normalized_height = _clamp_qwen_size(
        _round_to_multiple(height_value, QWEN_LATENT_MULTIPLE)
    )
    return normalized_width, normalized_height


def _resolve_aspect_ratio(aspect_ratio: str | tuple[int, int]) -> tuple[int, int]:
    if isinstance(aspect_ratio, tuple) and len(aspect_ratio) == 2:
        ratio_width, ratio_height = aspect_ratio
    else:
        try:
            ratio_width, ratio_height = ASPECT_RATIOS[str(aspect_ratio)]
        except KeyError:
            try:
                raw_width, raw_height = str(aspect_ratio).split(":", 1)
                ratio_width, ratio_height = int(raw_width), int(raw_height)
            except (ValueError, TypeError) as exc:
                raise ValueError(f"unsupported aspect ratio: {aspect_ratio}") from exc

    if ratio_width <= 0 or ratio_height <= 0:
        raise ValueError("aspect ratio values must be positive")
    return int(ratio_width), int(ratio_height)


def calculate_qwen_resolution(
    aspect_ratio: str | tuple[int, int],
    megapixels: float,
) -> tuple[int, int]:
    """Calculate an aspect-preserving Qwen output size.

    The official Resolution Selector uses 8-pixel alignment. Qwen Image 2.1
    creates its latent at a 16-pixel spatial stride, so this node aligns the
    final output to 16 pixels instead.
    """

    ratio_width, ratio_height = _resolve_aspect_ratio(aspect_ratio)
    try:
        megapixels_value = float(megapixels)
    except (TypeError, ValueError) as exc:
        raise ValueError("megapixels must be numeric") from exc

    if not math.isfinite(megapixels_value) or megapixels_value <= 0:
        raise ValueError("megapixels must be greater than zero")

    total_pixels = megapixels_value * 1024 * 1024
    scale = math.sqrt(total_pixels / (ratio_width * ratio_height))
    width = _round_to_multiple(ratio_width * scale, QWEN_LATENT_MULTIPLE)
    height = _round_to_multiple(ratio_height * scale, QWEN_LATENT_MULTIPLE)
    return normalize_custom_resolution(width, height)


def resolve_output_resolution(
    resolution_mode: str,
    aspect_ratio: str,
    megapixels: float,
    width: int,
    height: int,
) -> tuple[int, int]:
    if resolution_mode == "custom":
        return normalize_custom_resolution(width, height)
    if resolution_mode != "aspect_ratio_megapixels":
        raise ValueError(f"unsupported resolution mode: {resolution_mode}")
    return calculate_qwen_resolution(aspect_ratio, megapixels)


def build_qwen_latent(batch_size: int, width: int, height: int) -> dict[str, torch.Tensor]:
    """Build the 64-channel latent expected by Qwen Image 2.1."""

    try:
        batch = int(batch_size)
    except (TypeError, ValueError) as exc:
        raise ValueError("batch_size must be an integer") from exc
    if batch < 1 or batch > 64:
        raise ValueError("batch_size must be between 1 and 64")

    normalized_width, normalized_height = normalize_custom_resolution(width, height)
    import comfy.model_management

    samples = torch.zeros(
        [
            batch,
            64,
            normalized_height // QWEN_LATENT_MULTIPLE,
            normalized_width // QWEN_LATENT_MULTIPLE,
        ],
        device=comfy.model_management.intermediate_device(),
    )
    return {"samples": samples}


def _empty_hidden_input(default: str = "") -> tuple[str, dict[str, Any]]:
    return ("STRING", {"default": default, "multiline": True, "hidden": True})


class RyanQwenImage21:
    """A focused wrapper around ComfyUI's Qwen Image 2.1 text encoder."""

    @classmethod
    def INPUT_TYPES(cls):
        optional: dict[str, tuple] = {
            "vae": ("VAE",),
        }
        for index in range(1, MAX_IMAGE_SLOTS + 1):
            optional[f"image_{index:02d}"] = ("IMAGE",)
            optional[f"gallery_{index:02d}"] = _empty_hidden_input()

        hidden = {
            "gallery_manifest": _empty_hidden_input("[]"),
            "prompt_mentions": _empty_hidden_input("[]"),
        }
        return {
            "required": {
                "clip": ("CLIP",),
                "prompt": ("STRING", {"default": "", "multiline": True}),
                "negative_prompt": ("STRING", {"default": "", "multiline": True}),
                "resolution_mode": (
                    ["aspect_ratio_megapixels", "custom"],
                    {"default": "aspect_ratio_megapixels"},
                ),
                "aspect_ratio": (list(ASPECT_RATIOS.keys()), {"default": "1:1 (Square)"}),
                "megapixels": (
                    "FLOAT",
                    {"default": 2.0, "min": 0.1, "max": 16.0, "step": 0.1},
                ),
                "width": (
                    "INT",
                    {"default": 1024, "min": MIN_QWEN_SIZE, "max": MAX_QWEN_SIZE, "step": 16},
                ),
                "height": (
                    "INT",
                    {"default": 1024, "min": MIN_QWEN_SIZE, "max": MAX_QWEN_SIZE, "step": 16},
                ),
                "batch_size": ("INT", {"default": 1, "min": 1, "max": 64, "step": 1}),
                "reference_resolution": (
                    "INT",
                    {"default": 1024, "min": 0, "max": MAX_QWEN_SIZE, "step": 32},
                ),
                "image_slot_count": ("INT", {"default": 2, "min": 0, "max": MAX_IMAGE_SLOTS, "step": 1}),
            },
            "optional": optional,
            "hidden": hidden,
        }

    RETURN_TYPES = ("CONDITIONING", "CONDITIONING", "LATENT")
    RETURN_NAMES = ("positive", "negative", "latent")
    FUNCTION = "encode"
    CATEGORY = "Ryan/Conditioning"
    DESCRIPTION = "Qwen Image 2.1 Prompt、参考图和输出 latent 节点。"

    def encode(
        self,
        clip,
        prompt: str,
        negative_prompt: str,
        resolution_mode: str,
        aspect_ratio: str,
        megapixels: float,
        width: int,
        height: int,
        batch_size: int,
        reference_resolution: int,
        image_slot_count: int = 2,
        vae=None,
        gallery_manifest: str = "[]",
        prompt_mentions: str = "[]",
        **kwargs,
    ):
        del reference_resolution, gallery_manifest, prompt_mentions, vae
        output_width, output_height = resolve_output_resolution(
            resolution_mode,
            aspect_ratio,
            megapixels,
            width,
            height,
        )

        # Image inputs are intentionally ignored in Task 1. The image
        # collection and Qwen vision path are added in the gallery slice.
        del image_slot_count, kwargs
        images_vl: list[torch.Tensor] = []
        keep_vision = True
        positive_tokens = clip.tokenize(
            prompt,
            images=images_vl,
            keep_vision=keep_vision,
            prevent_empty_text=True,
        )
        negative_tokens = clip.tokenize(
            negative_prompt,
            images=images_vl,
            keep_vision=keep_vision,
            prevent_empty_text=True,
        )
        positive = clip.encode_from_tokens_scheduled(positive_tokens)
        negative = clip.encode_from_tokens_scheduled(negative_tokens)
        latent = build_qwen_latent(batch_size, output_width, output_height)
        return (positive, negative, latent)


__all__ = [
    "ASPECT_RATIOS",
    "MAX_IMAGE_SLOTS",
    "RyanQwenImage21",
    "build_qwen_latent",
    "calculate_qwen_resolution",
    "normalize_custom_resolution",
    "resolve_output_resolution",
]
