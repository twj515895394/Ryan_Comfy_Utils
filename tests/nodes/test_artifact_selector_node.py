import json
import unittest
from dataclasses import replace
from ryan_comfy_utils.nodes.artifact_selector_node import RyanArtifactSelector
from ryan_comfy_utils.workflow_agent.models import RyanContext, RyanContextEntry


class TestArtifactSelectorNode(unittest.TestCase):
    def _run(self, **kwargs):
        return RyanArtifactSelector().run(**kwargs)["result"]

    def _context(self):
        return RyanContext(
            workflow_id="wf_selector",
            entries=[
                RyanContextEntry(
                    entry_id="entry_v1",
                    workflow_id="wf_selector",
                    source_agent_uid="agent_art",
                    kind="production.design",
                    revision=1,
                    content="legacy body",
                    metadata={
                        "artifact_bundle": {
                            "artifact_type": "production_design",
                            "content": {},
                            "outputs": [
                                {"output_id": "image_01", "kind": "image_prompt", "label": "主视觉", "text": "IMAGE"},
                                {
                                    "output_id": "storyboard_01",
                                    "kind": "storyboard_sheet_prompt",
                                    "label": "分镜表",
                                    "text": "STORYBOARD",
                                },
                            ],
                            "shots": [
                                {"shot_id": "shot_01", "kind": "shot_prompt", "label": "镜头一", "prompt": "SHOT"}
                            ],
                        }
                    },
                )
            ],
        )

    def test_declares_semantic_inputs_after_legacy_inputs(self):
        names = list(RyanArtifactSelector.INPUT_TYPES()["required"])
        self.assertEqual(
            names[:6],
            ["source_agent_uid", "artifact_type", "output_id", "shot_id", "kind", "revision"],
        )
        self.assertEqual(
            names[6:],
            ["selection", "source_agent", "shot_scope", "purpose", "target_id"],
        )
        optional = RyanArtifactSelector.INPUT_TYPES()["optional"]
        self.assertIn("shot", optional)
        self.assertIn("context", optional)

    def test_dynamic_shot_queue_validation_accepts_runtime_label(self):
        optional = RyanArtifactSelector.INPUT_TYPES()["optional"]
        self.assertEqual(optional["shot"][0], "COMBO")
        self.assertEqual(optional["shot"][1]["options"], ["自动选择镜头"])
        self.assertTrue(
            RyanArtifactSelector.VALIDATE_INPUTS(
                shot="美术 / 资产设计 · 图像提示词 · SCENE_001 · 用途：scene_reference"
            )
        )

    def test_dynamic_shot_is_native_combo_for_frontend_dropdown(self):
        required = RyanArtifactSelector.INPUT_TYPES()["required"]
        optional = RyanArtifactSelector.INPUT_TYPES()["optional"]
        self.assertEqual(required["selection"][0], "COMBO")
        self.assertEqual(optional["shot"][0], "COMBO")
        self.assertEqual(optional["shot"][1]["default"], "自动选择镜头")
 
    def test_dynamic_shot_combo_contains_real_target_values_after_context(self):
        context = self._context()
        context.entries[0].metadata["artifact_bundle"]["outputs"][0]["target_ids"] = [
            "SCENE_001",
            "CHAR_001",
        ]
        bundle = context.entries[0].metadata["artifact_bundle"]
        self.assertEqual(bundle["outputs"][0]["target_ids"], ["SCENE_001", "CHAR_001"])
        result = self._run(context=context, selection="image_prompt", target_id="SCENE_001")
        self.assertEqual(result, ("IMAGE",))


    def test_auto_shot_alias_is_accepted_for_legacy_widgets(self):
        result = self._run(
            context=self._context(),
            selection="shot_prompt",
            shot_scope="selected",
            shot="自动选择对象",
        )
        self.assertEqual(result, ("",))

    def test_selected_dynamic_shot_label_is_accepted(self):
        result = self._run(
            context=self._context(),
            selection="shot_prompt",
            shot_scope="selected",
            shot="镜头一",
        )
        self.assertEqual(result, ("SHOT",))
    def test_full_dynamic_output_label_resolves_to_output_id(self):
        result = self._run(
            context=self._context(),
            selection="image_prompt",
            shot="上游 Agent · 图像提示词 · 未指定对象",
        )
        self.assertEqual(result, ("IMAGE",))

    def test_result_exposes_selected_text_and_context_to_comfy_ui(self):
        result = RyanArtifactSelector().run(context=self._context())
        self.assertEqual(result["result"], ("legacy body",))
        self.assertEqual(result["ui"]["text"], ["legacy body"])
        context_json = result["ui"]["context_json"]
        self.assertEqual(len(context_json), 1)
        self.assertEqual(json.loads(context_json[0])["workflow_id"], "wf_selector")

    def test_default_selector_is_automatic(self):
        result = self._run(context=self._context())
        self.assertEqual(result, ("legacy body",))

    def test_selects_image_prompt_by_semantic_selection(self):
        result = self._run(context=self._context(), selection="image_prompt")
        self.assertEqual(result, ("IMAGE",))

    def test_selects_storyboard_prompt_by_semantic_selection(self):
        result = self._run(context=self._context(), selection="storyboard_prompt")
        self.assertEqual(result, ("STORYBOARD",))

    def test_selects_selected_shot_by_semantic_selection(self):
        result = self._run(
            context=self._context(),
            selection="shot_prompt",
            shot_scope="selected",
            shot="shot_01",
        )
        self.assertEqual(result, ("SHOT",))

    def test_semantic_selection_never_falls_back_to_entry_body(self):
        result = self._run(context=self._context(), selection="video_prompt")
        self.assertEqual(result, ("",))

    def test_legacy_internal_fields_take_precedence(self):
        result = self._run(
            context=self._context(),
            selection="video_prompt",
            artifact_type="production_design",
            output_id="image_01",
        )
        self.assertEqual(result, ("IMAGE",))

    def test_selects_output_by_id_and_type(self):
        result = self._run(
            context=self._context(), artifact_type="production_design", output_id="image_01"
        )
        self.assertEqual(result, ("IMAGE",))

    def test_selects_shot_and_revision(self):
        result = self._run(context=self._context(), shot_id="shot_01", revision=1)
        self.assertEqual(result, ("SHOT",))

    def test_no_match_returns_empty_without_body_fallback(self):
        result = self._run(context=self._context(), output_id="missing")
        self.assertEqual(result, ("",))

    def test_missing_context_is_empty(self):
        self.assertEqual(self._run(), ("",))

    def test_auto_selection_returns_canonical_body_not_arbitrary_prompt(self):
        base = self._context().entries[0]
        context = RyanContext(
            workflow_id="wf_selector",
            entries=[replace(base, content="CANONICAL BODY")],
        )
        self.assertEqual(
            self._run(context=context, selection="auto"),
            ("CANONICAL BODY",),
        )

    def test_default_selection_uses_latest_entry_body_without_parameters(self):
        base = self._context().entries[0]
        context = RyanContext(
            workflow_id="wf_selector",
            entries=[replace(base, metadata={}, content="DEFAULT CANONICAL BODY")],
        )
        self.assertEqual(self._run(context=context), ("DEFAULT CANONICAL BODY",))

    def test_invalid_artifact_still_allows_default_body_selection(self):
        base = self._context().entries[0]
        context = RyanContext(
            workflow_id="wf_selector",
            entries=[
                replace(
                    base,
                    metadata={
                        "artifact_status": "invalid",
                        "artifact_error": "output_id must be a non-empty path component",
                    },
                    content="INVALID BUNDLE CANONICAL BODY",
                )
            ],
        )
        self.assertEqual(
            self._run(context=context),
            ("INVALID BUNDLE CANONICAL BODY",),
        )



    def test_accepts_display_semantic_values(self):
        result = self._run(
            context=self._context(),
            selection="指定镜头提示词",
            source_agent="agent_art",
            shot_scope="指定镜头",
            shot="镜头一",
        )
        self.assertEqual(result, ("SHOT",))

    def test_storyboard_selection_falls_back_to_shot_prompt(self):
        context = self._context()
        context.entries[0].metadata["artifact_bundle"]["outputs"] = [
            {"output_id": "image_01", "kind": "image_prompt", "label": "主视觉", "text": "IMAGE"}
        ]
        result = self._run(context=context, selection="storyboard_prompt")
        self.assertEqual(result, ("SHOT",))

    def test_selects_legacy_prompt_from_agent_context(self):
        base = self._context().entries[0]
        legacy = (
            "# Legacy Canon\n\n```ryan-artifact\n"
            '{"artifact_type":"production_design","revision":2,"outputs":['
            '{"kind":"image_prompt","id":"P01","role":"主视觉","prompt":"LEGACY IMAGE"}]}'
            "\n```\n"
        )
        context = RyanContext(
            workflow_id="wf_selector",
            entries=[
                replace(
                    base,
                    metadata={
                        "artifact_status": "invalid",
                        "artifact_error": "output_id must be a non-empty path component",
                    },
                    content=legacy,
                )
            ],
        )

        self.assertEqual(
            self._run(context=context, selection="image_prompt"),
            ("LEGACY IMAGE",),
        )

    def test_first_output_includes_shots(self):
        base = self._context().entries[0]
        context = RyanContext(
            workflow_id="wf_selector",
            entries=[replace(
                base,
                metadata={
                    "artifact_bundle": {
                        "artifact_type": "production_design",
                        "content": {},
                        "outputs": [],
                        "shots": [{"shot_id": "shot_only", "kind": "shot_prompt", "label": "镜头", "prompt": "SHOT ONLY"}],
                    }
                },
            )],
        )
        self.assertEqual(
            self._run(context=context, selection="first_output"),
            ("SHOT ONLY",),
        )

    def test_semantic_selection_stays_in_latest_entry(self):
        base = self._context().entries[0]
        latest = replace(
            base,
            entry_id="entry_v2",
            revision=2,
            metadata={
                "artifact_bundle": {
                    "artifact_type": "production_design",
                    "content": {},
                    "outputs": [{"output_id": "video_01", "kind": "video_prompt", "label": "视频", "text": "VIDEO"}],
                    "shots": [],
                }
            },
        )
        context = RyanContext(workflow_id="wf_selector", entries=[base, latest])
        self.assertEqual(
            self._run(context=context, selection="image_prompt"),
            ("",),
        )

    def test_selected_shot_without_value_returns_empty(self):
        self.assertEqual(
            self._run(
                context=self._context(),
                selection="shot_prompt",
                shot_scope="selected",
                shot="auto",
            ),
            ("",),
        )

    def test_semantic_selection_scans_all_stage_agents(self):
        base = self._context().entries[0]
        video_entry = replace(
            base,
            entry_id="entry_video",
            source_agent_uid="agent_video",
            source_agent_name="视频提示词导演",
            kind="video.prompts",
            revision=1,
            metadata={
                "artifact_bundle": {
                    "artifact_type": "video_prompts",
                    "content": {},
                    "outputs": [
                        {
                            "output_id": "SEG_001_VIDEO",
                            "kind": "video_prompt",
                            "label": "SEG_001 视频",
                            "text": "VIDEO",
                        }
                    ],
                    "shots": [],
                }
            },
        )
        context = RyanContext(workflow_id="wf_selector", entries=[base, video_entry])

        self.assertEqual(self._run(context=context, selection="image_prompt"), ("IMAGE",))
        self.assertEqual(self._run(context=context, selection="video_prompt"), ("VIDEO",))

    def test_missing_optional_shot_does_not_break_image_selection(self):
        result = self._run(context=self._context(), selection="image_prompt")
        self.assertEqual(result, ("IMAGE",))

    def test_resolves_full_frontend_display_label_to_output(self):
        context = self._context()
        context.entries[0] = replace(context.entries[0], source_agent_name="美术 / 资产设计")
        output = context.entries[0].metadata["artifact_bundle"]["outputs"][0]
        output["target_ids"] = ["SCENE_001"]
        output["purpose"] = "scene_reference"
        label = "美术 / 资产设计 · 图像提示词 · SCENE_001 · 用途：scene_reference"
        result = self._run(context=context, selection="image_prompt", shot=label)
        self.assertEqual(result, ("IMAGE",))

if __name__ == "__main__":
    unittest.main()
