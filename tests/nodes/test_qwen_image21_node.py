from __future__ import annotations

import math

import torch

from ryan_comfy_utils.nodes.qwen_image21_node import (
    ASPECT_RATIOS,
    RyanQwenImage21,
    build_qwen_latent,
    calculate_qwen_resolution,
    collect_image_sources,
    normalize_custom_resolution,
    prepare_qwen_reference_images,
    replace_prompt_mentions,
    resolve_image_mentions,
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


class FakeVAE:
    def __init__(self):
        self.inputs = []

    def encode(self, image):
        self.inputs.append(image)
        return {"reference": len(self.inputs), "shape": tuple(image.shape)}


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


def test_external_images_are_collected_in_slot_order_and_compacted():
    first = torch.zeros((2, 32, 48, 3), dtype=torch.float32)
    second = torch.zeros((1, 40, 24, 3), dtype=torch.float32)
    assets = collect_image_sources(
        {"image_01": first, "image_02": None, "image_03": second},
        {},
        "[]",
    )

    assert [asset["slot"] for asset in assets] == [1, 3]
    assert [asset["asset_id"] for asset in assets] == [
        "external-slot-01",
        "external-slot-03",
    ]
    assert [asset["image"].shape[0] for asset in assets] == [1, 1]


def test_external_image_wins_over_same_slot_gallery_image():
    image = torch.zeros((1, 32, 32, 3), dtype=torch.float32)
    assets = collect_image_sources(
        {"image_01": image},
        {"gallery_01": "missing-gallery-file.png"},
        "[]",
    )

    assert len(assets) == 1
    assert assets[0]["source"] == "external"


def test_missing_gallery_image_raises_a_readable_error():
    try:
        collect_image_sources(
            {"image_01": None},
            {"gallery_01": "missing-gallery-file.png"},
            "[]",
        )
    except ValueError as exc:
        assert "gallery file does not exist" in str(exc)
    else:
        raise AssertionError("a missing gallery file should fail")


def test_reference_images_are_resized_and_alpha_is_composited_for_vision():
    rgba = torch.zeros((1, 32, 48, 4), dtype=torch.float32)
    rgba[:, :, :, 0] = 1.0
    rgba[:, :, :, 3] = 0.5
    images_vl, ref_latents = prepare_qwen_reference_images(
        [{"asset_id": "a", "image": rgba}],
        reference_resolution=0,
    )

    assert ref_latents == []
    assert images_vl[0].shape[-1] == 3
    assert images_vl[0].shape[1:3] == (32, 64)
    assert torch.allclose(images_vl[0][:, 0, 0, 0], torch.tensor([1.0]))
    assert torch.allclose(images_vl[0][:, 0, 0, 1], torch.tensor([0.5]), atol=0.01)


def test_node_passes_all_external_images_to_qwen_without_vae():
    clip = FakeClip()
    image = torch.zeros((1, 32, 32, 3), dtype=torch.float32)
    RyanQwenImage21().encode(
        clip=clip,
        prompt="combine references",
        negative_prompt="blurry",
        resolution_mode="custom",
        aspect_ratio="1:1 (Square)",
        megapixels=2.0,
        width=1024,
        height=1024,
        batch_size=1,
        reference_resolution=0,
        image_slot_count=2,
        image_01=image,
        image_02=image,
    )

    assert len(clip.tokenize_calls) == 2
    assert all(len(call[1]["images"]) == 2 for call in clip.tokenize_calls)
    assert all(call[1]["keep_vision"] is True for call in clip.tokenize_calls)


def test_mentions_resolve_by_stable_asset_id_after_reordering():
    original_assets = [
        {"asset_id": "character", "filename": "character.png"},
        {"asset_id": "clothing", "filename": "clothing.png"},
    ]
    reordered_assets = [original_assets[1], original_assets[0]]
    manifest = [{"field": "positive", "display": "@图片1", "asset_id": "character"}]

    resolved = resolve_image_mentions("@图片1 是身份参考", reordered_assets, manifest)
    assert resolved[0]["asset_id"] == "character"
    assert resolved[0]["ordinal"] == 2
    assert replace_prompt_mentions("@图片1 是身份参考", reordered_assets, manifest) == "Picture 2 是身份参考"


def test_manual_mentions_use_current_compact_ordinal():
    assets = [
        {"asset_id": "a"},
        {"asset_id": "b"},
    ]
    assert replace_prompt_mentions("@image2 is clothing", assets) == "Picture 2 is clothing"


def test_invalid_and_missing_mentions_raise_readable_errors():
    assets = [{"asset_id": "a"}]
    try:
        resolve_image_mentions("@图片2", assets)
    except ValueError as exc:
        assert "超出当前有效参考图范围" in str(exc)
    else:
        raise AssertionError("an out-of-range mention should fail")

    try:
        resolve_image_mentions(
            "@图片1",
            assets,
            [{"field": "positive", "display": "@图片1", "asset_id": "deleted"}],
        )
    except ValueError as exc:
        assert "参考图已不存在" in str(exc)
    else:
        raise AssertionError("a deleted mentioned asset should fail")


def test_positive_and_negative_mentions_use_separate_manifest_fields():
    assets = [{"asset_id": "character"}, {"asset_id": "clothing"}]
    manifest = [
        {"field": "positive", "display": "@图片1", "asset_id": "character"},
        {"field": "negative", "display": "@图片1", "asset_id": "clothing"},
    ]
    assert replace_prompt_mentions("@图片1", assets, manifest, field="positive") == "Picture 1"
    assert replace_prompt_mentions("@图片1", assets, manifest, field="negative") == "Picture 2"


def test_node_replaces_mentions_before_qwen_tokenization():
    clip = FakeClip()
    image = torch.zeros((1, 32, 32, 3), dtype=torch.float32)
    RyanQwenImage21().encode(
        clip=clip,
        prompt="@图片1 is the identity",
        negative_prompt="not @image1",
        resolution_mode="custom",
        aspect_ratio="1:1 (Square)",
        megapixels=2.0,
        width=1024,
        height=1024,
        batch_size=1,
        reference_resolution=0,
        image_slot_count=1,
        prompt_mentions="[]",
        image_01=image,
    )

    assert clip.tokenize_calls[0][0] == "Picture 1 is the identity"
    assert clip.tokenize_calls[1][0] == "not Picture 1"


def test_vae_reference_latents_are_appended_to_both_conditionings(monkeypatch):
    import node_helpers

    conditioning_calls = []

    def fake_conditioning_set_values(conditioning, values, append=False):
        conditioning_calls.append((conditioning, values, append))
        return {"conditioning": conditioning, "values": values}

    monkeypatch.setattr(node_helpers, "conditioning_set_values", fake_conditioning_set_values)
    clip = FakeClip()
    vae = FakeVAE()
    image = torch.zeros((1, 32, 48, 4), dtype=torch.float32)

    outputs = RyanQwenImage21().encode(
        clip=clip,
        prompt="keep the character",
        negative_prompt="wrong face",
        resolution_mode="custom",
        aspect_ratio="1:1 (Square)",
        megapixels=2.0,
        width=1024,
        height=768,
        batch_size=1,
        reference_resolution=0,
        image_slot_count=1,
        vae=vae,
        image_01=image,
    )

    assert len(vae.inputs) == 1
    assert vae.inputs[0].shape == (1, 32, 64, 4)
    assert len(conditioning_calls) == 2
    assert all(call[2] is True for call in conditioning_calls)
    assert all(call[1]["reference_latents"] == [{"reference": 1, "shape": (1, 32, 64, 4)}] for call in conditioning_calls)
    assert all(call[1]["reference_latents"] for call in conditioning_calls)
    assert outputs[2]["samples"].shape == (1, 64, 48, 64)
    assert all(call[1]["keep_vision"] is False for call in clip.tokenize_calls)
