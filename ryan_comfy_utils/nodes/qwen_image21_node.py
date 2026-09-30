"""Ryan Qwen Image 2.1 conditioning and latent node."""

from __future__ import annotations

import math
import json
import re
import unicodedata
from pathlib import Path
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

MEGAPIXEL_OPTIONS = (0.5, 0.75, 0.98, 1.0, 1.5, 2.0, 3.0, 4.0)
DEFAULT_MEGAPIXELS = 2.0

MAX_IMAGE_SLOTS = 16
MIN_QWEN_SIZE = 16
MAX_QWEN_SIZE = 4096
QWEN_LATENT_MULTIPLE = 16
QWEN_REFERENCE_MULTIPLE = 32
IMAGE_MENTION_PATTERN = re.compile(r"@(?:图片|image)(\d+)")


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


def image_slot_name(index: int) -> str:
    if index < 1 or index > MAX_IMAGE_SLOTS:
        raise ValueError(f"image slot index must be 1..{MAX_IMAGE_SLOTS}")
    return f"image_{index:02d}"


def gallery_slot_name(index: int) -> str:
    if index < 1 or index > MAX_IMAGE_SLOTS:
        raise ValueError(f"gallery slot index must be 1..{MAX_IMAGE_SLOTS}")
    return f"gallery_{index:02d}"


def _parse_gallery_manifest(value: str | list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    if not value:
        return []
    if isinstance(value, list):
        data = value
    else:
        try:
            data = json.loads(value)
        except (TypeError, json.JSONDecodeError) as exc:
            raise ValueError("gallery_manifest must be valid JSON") from exc
    if not isinstance(data, list):
        raise ValueError("gallery_manifest must be a JSON list")
    return [item for item in data if isinstance(item, dict)]


def _manifest_entry_for_slot(
    manifest: list[dict[str, Any]],
    slot: int,
) -> dict[str, Any]:
    for entry in manifest:
        entry_slot = entry.get("slot", entry.get("source_slot"))
        try:
            if int(entry_slot) == slot:
                return entry
        except (TypeError, ValueError):
            continue
    return {}


def _annotated_path_from_value(value: Any) -> str:
    if isinstance(value, str):
        return value
    if not isinstance(value, dict):
        return ""
    name = str(value.get("name") or "")
    subfolder = str(value.get("subfolder") or "").strip("/")
    file_type = str(value.get("type") or "input")
    if not name:
        return ""
    raw = f"{subfolder}/{name}" if subfolder else name
    if file_type and file_type != "input":
        raw = f"{raw} [type={file_type}]"
    return raw


def _gallery_path_candidate(value: Any) -> str:
    """Return a gallery path, ignoring stale numeric widget placeholders.

    Gallery slots are hidden STRING widgets. Older serialized nodes can leave
    a control value such as ``"1"`` in one of those widgets after the visible
    widget order changes. It is not a file path and must not turn a text-only
    generation into a failed reference-image load.
    """

    path = _strip_gallery_invisible(_annotated_path_from_value(value))
    # ComfyUI widget serialization can preserve zero-width/BOM characters in
    # an empty hidden field. Remove those before deciding whether this is a
    # real gallery path.
    if not path or re.fullmatch(r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)", path):
        return ""
    return path


def _strip_gallery_invisible(value: str) -> str:
    """Remove control/format characters from a serialized gallery value."""

    return "".join(
        character
        for character in str(value)
        if unicodedata.category(character) not in {"Cc", "Cf", "Cs"}
    ).strip()


def _load_gallery_image(annotated_path: str) -> torch.Tensor:
    annotated_path = _strip_gallery_invisible(annotated_path)
    if not annotated_path:
        raise ValueError("gallery image path is empty")

    import folder_paths
    import node_helpers
    import numpy as np
    from PIL import Image, ImageOps

    if not folder_paths.exists_annotated_filepath(annotated_path):
        raise ValueError(f"Ryan Qwen Image 2.1 gallery file does not exist: {annotated_path}")

    path = folder_paths.get_annotated_filepath(annotated_path)
    image = node_helpers.pillow(Image.open, path)
    image = node_helpers.pillow(ImageOps.exif_transpose, image)
    mode = "RGBA" if "A" in image.getbands() else "RGB"
    array = np.asarray(image.convert(mode)).astype(np.float32) / 255.0
    return torch.from_numpy(array)[None, ...]


def collect_image_sources(
    image_slots: dict[str, Any],
    gallery_slots: dict[str, str],
    gallery_manifest: str | list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Collect external and gallery images in stable slot order.

    External IMAGE tensors take precedence over the gallery in the same slot.
    The returned records are compacted by active slot while retaining a stable
    asset id for later mention resolution.
    """

    manifest = _parse_gallery_manifest(gallery_manifest)
    assets: list[dict[str, Any]] = []
    for slot in range(1, MAX_IMAGE_SLOTS + 1):
        image = image_slots.get(image_slot_name(slot))
        entry = _manifest_entry_for_slot(manifest, slot)
        if image is not None:
            assets.append(
                {
                    "asset_id": f"external-slot-{slot:02d}",
                    "source": "external",
                    "slot": slot,
                    "filename": entry.get("filename") or f"image_{slot:02d}",
                    "image": image[:1],
                }
            )
            continue

        gallery_value = gallery_slots.get(gallery_slot_name(slot))
        # gallery_* fields are hidden execution mirrors. The manifest is the
        # source of truth for whether a gallery slot actually contains a
        # reference image; this prevents stale serialized widget values from
        # turning text-to-image runs into empty-path file errors.
        if not entry:
            continue
        path_value = _gallery_path_candidate(gallery_value)
        if not path_value:
            path_value = _gallery_path_candidate(entry.get("path") or entry.get("annotated_path"))
        if not path_value:
            continue
        assets.append(
            {
                "asset_id": entry.get("asset_id") or f"gallery-slot-{slot:02d}",
                "source": "gallery",
                "slot": slot,
                "filename": entry.get("filename") or Path(path_value).name,
                "path": path_value,
                "image": _load_gallery_image(path_value),
            }
        )
    return assets


def _resize_reference_image(image: torch.Tensor, reference_resolution: int) -> torch.Tensor:
    import comfy.utils

    samples = image[:1].movedim(-1, 1)
    if reference_resolution > 0:
        ratio = samples.shape[3] / samples.shape[2]
        width = round(math.sqrt(reference_resolution * reference_resolution * ratio) / QWEN_REFERENCE_MULTIPLE) * QWEN_REFERENCE_MULTIPLE
        height = round(math.sqrt(reference_resolution * reference_resolution / ratio) / QWEN_REFERENCE_MULTIPLE) * QWEN_REFERENCE_MULTIPLE
    else:
        width = round(samples.shape[3] / QWEN_REFERENCE_MULTIPLE) * QWEN_REFERENCE_MULTIPLE
        height = round(samples.shape[2] / QWEN_REFERENCE_MULTIPLE) * QWEN_REFERENCE_MULTIPLE

    width = max(QWEN_REFERENCE_MULTIPLE, width)
    height = max(QWEN_REFERENCE_MULTIPLE, height)
    if (width, height) == (samples.shape[3], samples.shape[2]):
        return image[:1]
    return comfy.utils.common_upscale(samples, width, height, "lanczos", "disabled").movedim(1, -1)


def prepare_qwen_reference_images(
    assets: list[dict[str, Any]],
    reference_resolution: int,
    vae=None,
) -> tuple[list[torch.Tensor], list[torch.Tensor]]:
    images_vl: list[torch.Tensor] = []
    ref_latents: list[torch.Tensor] = []
    for asset in assets:
        resized = _resize_reference_image(asset["image"], int(reference_resolution))
        rgb = resized[:, :, :, :3]
        if resized.shape[-1] > 3:
            rgb = rgb * resized[:, :, :, 3:] + (1.0 - resized[:, :, :, 3:])
        images_vl.append(rgb)
        if vae is not None:
            ref_latents.append(vae.encode(resized))
    return images_vl, ref_latents


def _parse_prompt_mentions(value: str | list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    if not value:
        return []
    if isinstance(value, list):
        data = value
    else:
        try:
            data = json.loads(value)
        except (TypeError, json.JSONDecodeError) as exc:
            raise ValueError("prompt_mentions must be valid JSON") from exc
    if not isinstance(data, list):
        raise ValueError("prompt_mentions must be a JSON list")
    return [item for item in data if isinstance(item, dict)]


def resolve_image_mentions(
    prompt: str,
    active_assets: list[dict[str, Any]],
    manifest: str | list[dict[str, Any]] | None = None,
    *,
    field: str = "positive",
) -> list[dict[str, Any]]:
    """Resolve image mentions to the current compact image ordinal.

    A saved manifest binds a mention to an asset id. Hand-written text without
    a manifest falls back to the current compact ordinal for compatibility.
    """

    prompt_text = str(prompt or "")
    mention_manifest = _parse_prompt_mentions(manifest)
    matching_manifest = [
        item for item in mention_manifest if item.get("field", item.get("prompt", "positive")) == field
    ]
    used_manifest_indexes: set[int] = set()
    assets_by_id = {
        str(asset.get("asset_id")): (index + 1, asset)
        for index, asset in enumerate(active_assets)
        if asset.get("asset_id")
    }
    resolved: list[dict[str, Any]] = []
    for match in IMAGE_MENTION_PATTERN.finditer(prompt_text):
        token = match.group(0)
        ordinal_from_text = int(match.group(1))
        manifest_entry = None
        manifest_index = None
        for index, item in enumerate(matching_manifest):
            if index in used_manifest_indexes:
                continue
            if str(item.get("display") or token) == token:
                manifest_entry = item
                manifest_index = index
                break

        asset = None
        ordinal = None
        if manifest_entry is not None and manifest_entry.get("asset_id"):
            asset_result = assets_by_id.get(str(manifest_entry["asset_id"]))
            if asset_result is None:
                raise ValueError(
                    f"Ryan Qwen Image 2.1: {token} 指向的参考图已不存在，请重新上传图片或删除该引用。"
                )
            ordinal, asset = asset_result
            used_manifest_indexes.add(manifest_index)
        else:
            if ordinal_from_text < 1 or ordinal_from_text > len(active_assets):
                raise ValueError(
                    f"Ryan Qwen Image 2.1: {token} 超出当前有效参考图范围（共 {len(active_assets)} 张）。"
                )
            ordinal = ordinal_from_text
            asset = active_assets[ordinal - 1]

        resolved.append(
            {
                "token": token,
                "start": match.start(),
                "end": match.end(),
                "ordinal": ordinal,
                "asset_id": asset.get("asset_id"),
                "asset": asset,
            }
        )
    return resolved


def replace_prompt_mentions(
    prompt: str,
    active_assets: list[dict[str, Any]],
    manifest: str | list[dict[str, Any]] | None = None,
    *,
    field: str = "positive",
) -> str:
    resolved = resolve_image_mentions(prompt, active_assets, manifest, field=field)
    if not resolved:
        return str(prompt or "")
    output = str(prompt or "")
    for mention in reversed(resolved):
        output = output[: mention["start"]] + f"Picture {mention['ordinal']}" + output[mention["end"] :]
    return output


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

        optional["gallery_manifest"] = _empty_hidden_input("[]")
        optional["prompt_mentions"] = _empty_hidden_input("[]")
        return {
            "required": {
                "clip": ("CLIP",),
                # Keep this as a normal ComfyUI multiline widget with a
                # connectable STRING socket, matching the official Qwen
                # Image 2.1 node. The frontend places that socket beside
                # the custom Prompt editor instead of in the top input list.
                "prompt": (
                    "STRING",
                    {"default": "", "multiline": True, "dynamicPrompts": True},
                ),
                "negative_prompt": (
                    "STRING",
                    {"default": "", "multiline": True, "dynamicPrompts": True},
                ),
                "aspect_ratio": (list(ASPECT_RATIOS.keys()), {"default": "9:16 (Portrait Widescreen)"}),
                "megapixels": (
                    list(MEGAPIXEL_OPTIONS),
                    {"default": DEFAULT_MEGAPIXELS},
                ),
                "batch_size": ("INT", {"default": 1, "min": 1, "max": 64, "step": 1}),
                "resolution": (
                    "INT",
                    {"default": 1024, "min": 0, "max": MAX_QWEN_SIZE, "step": 32},
                ),
            },
            "optional": optional,
        }

    RETURN_TYPES = ("CONDITIONING", "CONDITIONING", "LATENT")
    RETURN_NAMES = ("positive", "negative", "latent")
    FUNCTION = "encode"
    CATEGORY = "Ryan/Conditioning"
    DESCRIPTION = "Qwen Image 2.1 Prompt、参考图和输出 latent 节点。"

    def encode(
        self,
        clip,
        negative_prompt: str,
        aspect_ratio: str,
        megapixels: float,
        batch_size: int,
        resolution: int = 1024,
        prompt: str | None = None,
        prompt_text: str = "",
        resolution_mode: str = "aspect_ratio_megapixels",
        width: int = 1024,
        height: int = 1024,
        image_slot_count: int = 2,
        reference_resolution: int | None = None,
        vae=None,
        gallery_manifest: str = "[]",
        prompt_mentions: str = "[]",
        **kwargs,
    ):
        if reference_resolution is not None:
            # Compatibility with the previous Ryan node schema.
            resolution = reference_resolution
        prompt = str(prompt if prompt is not None else prompt_text or "")
        output_width, output_height = resolve_output_resolution(
            resolution_mode,
            aspect_ratio,
            megapixels,
            width,
            height,
        )

        # These compatibility parameters are intentionally not exposed by
        # INPUT_TYPES anymore. They allow older serialized workflows to keep
        # executing while the node UI stays focused on Qwen's recommended
        # aspect-ratio/megapixel sizing and image gallery.
        del image_slot_count
        image_slots = {
            image_slot_name(index): kwargs.get(image_slot_name(index))
            for index in range(1, MAX_IMAGE_SLOTS + 1)
        }
        gallery_slots = {
            gallery_slot_name(index): kwargs.get(gallery_slot_name(index), "")
            for index in range(1, MAX_IMAGE_SLOTS + 1)
        }
        assets = collect_image_sources(image_slots, gallery_slots, gallery_manifest)
        prompt = replace_prompt_mentions(prompt, assets, prompt_mentions, field="positive")
        negative_prompt = replace_prompt_mentions(
            negative_prompt,
            assets,
            prompt_mentions,
            field="negative",
        )
        images_vl, ref_latents = prepare_qwen_reference_images(
            assets,
            int(resolution),
            vae=vae,
        )
        keep_vision = len(ref_latents) == 0
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
        if ref_latents:
            import node_helpers

            positive = node_helpers.conditioning_set_values(
                positive,
                {"reference_latents": ref_latents},
                append=True,
            )
            negative = node_helpers.conditioning_set_values(
                negative,
                {"reference_latents": ref_latents},
                append=True,
            )
        latent = build_qwen_latent(batch_size, output_width, output_height)
        return (positive, negative, latent)


__all__ = [
    "ASPECT_RATIOS",
    "DEFAULT_MEGAPIXELS",
    "MAX_IMAGE_SLOTS",
    "MEGAPIXEL_OPTIONS",
    "RyanQwenImage21",
    "build_qwen_latent",
    "calculate_qwen_resolution",
    "collect_image_sources",
    "normalize_custom_resolution",
    "prepare_qwen_reference_images",
    "replace_prompt_mentions",
    "resolve_image_mentions",
    "resolve_output_resolution",
]
