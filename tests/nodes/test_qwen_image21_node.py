from __future__ import annotations

import math

import torch

from ryan_comfy_utils.nodes.qwen_image21_node import (
    ASPECT_RATIOS,
    RyanQwenImage21,
    build_qwen_latent,
    calculate_qwen_resolution,
    normalize_custom_resolution,
    resolve_output_resolution,
)


class FakeClip:
    def __init__(self):
        self.tokenize_calls = []
        self.encoded = []

    def tokenize(self, text, **kwargs):
        self.tokenize_calls.append((text, kwargs))
        return {"text": text, **kwargs}

    def encode_from_tokens_scheduled(self, tokens):
        self.encoded.append(tokens)
        return [[tokens]]


def test_all_official_aspect_ratios_produce_aligned_dimensions():
    for aspect_ratio in ASPECT_RATIOS:
        width, height = calculate_qwen_resolution(aspect_ratio, 2.0)
        assert width % 16 == 0
        assert height % 16 == 0
        assert 16 <= width <= 4096
        assert 16 <= height <= 4096


def test_megapixels_preserves_aspect_ratio_with_reasonable_pixel_area():
    width, height = calculate_qwen_resolution("16:9 (Widescreen)", 2.0)
    assert math.isclose(width / height, 16 / 9, rel_tol=0.02)
    assert math.isclose(width * height, 2.0 * 1024 * 1024, rel_tol=0.03)


def test_custom_resolution_is_clamped_and_aligned():
    assert normalize_custom_resolution(1, 4095) == (16, 4096)
    assert resolve_output_resolution("custom", "1:1 (Square)", 2.0, 1023, 777) == (1024, 784)


def test_invalid_resolution_values_raise_clear_errors():
    for value in (0, -1, float("nan"), float("inf")):
        try:
            calculate_qwen_resolution("1:1 (Square)", value)
        except ValueError as exc:
            assert "megapixels" in str(exc)
        else:
            raise AssertionError("invalid megapixels should fail")

    try:
        resolve_output_resolution("unknown", "1:1 (Square)", 2.0, 1024, 1024)
    except ValueError as exc:
        assert "resolution mode" in str(exc)
    else:
        raise AssertionError("invalid mode should fail")


def test_qwen_latent_shape_and_channel_count():
    latent = build_qwen_latent(3, 1024, 768)
    assert latent["samples"].shape == (3, 64, 48, 64)
    assert latent["samples"].dtype == torch.float32


def test_node_input_contract_contains_qwen_controls_and_sixteen_slots():
    inputs = RyanQwenImage21.INPUT_TYPES()
    assert inputs["required"]["image_slot_count"][1]["max"] == 16
    assert inputs["required"]["batch_size"][1]["max"] == 64
    assert inputs["required"]["resolution_mode"][0] == [
        "aspect_ratio_megapixels",
        "custom",
    ]
    assert all(f"image_{index:02d}" in inputs["optional"] for index in range(1, 17))


def test_node_encodes_text_and_returns_qwen_latent_without_images():
    clip = FakeClip()
    outputs = RyanQwenImage21().encode(
        clip=clip,
        prompt="a red fox",
        negative_prompt="blurry",
        resolution_mode="custom",
        aspect_ratio="1:1 (Square)",
        megapixels=2.0,
        width=1024,
        height=768,
        batch_size=2,
        reference_resolution=1024,
        image_slot_count=0,
    )

    assert len(outputs) == 3
    assert outputs[2]["samples"].shape == (2, 64, 48, 64)
    assert [call[0] for call in clip.tokenize_calls] == ["a red fox", "blurry"]
    assert all(call[1]["images"] == [] for call in clip.tokenize_calls)
    assert all(call[1]["keep_vision"] is True for call in clip.tokenize_calls)
