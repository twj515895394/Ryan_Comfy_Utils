import json
import unittest
from pathlib import Path

from ryan_comfy_utils.workflow_agent.skill_contract import load_skill_contract


SKILLS_ROOT = Path("ryan_comfy_utils/acp/fixtures/skills")
EXPECTED = {
    "creative-story-planner": (
        "creative.story", "creative_story", ["concept_image_prompt"],
        {"concept_image_prompt": ["concept_art", "moodboard"]},
    ),
    "production-designer": (
        "production.design", "production_design", ["image_prompt"],
        {
            "image_prompt": [
                "character_reference", "character_sheet", "expression_sheet",
                "scene_reference", "spatial_reference", "prop_reference",
            ]
        },
    ),
    "script-director": ("script.direction", "script_direction", [], {}),
    "storyboard-director": (
        "storyboard.plan", "storyboard_plan",
        ["storyboard_prompt", "keyframe_prompt"],
        {
            "storyboard_prompt": ["control_storyboard", "style_storyboard"],
            "keyframe_prompt": ["start_frame", "end_frame", "reference_frame"],
        },
    ),
    "audio-director": (
        "audio.design", "audio_design", ["audio_prompt"],
        {"audio_prompt": ["music", "voice", "foley", "ambience"]},
    ),
    "video-prompt-director": (
        "video.prompts", "video_prompts", ["video_prompt"],
        {"video_prompt": ["segment_execution"]},
    ),
}


class TestSkillContracts(unittest.TestCase):
    def test_six_stage_contracts_have_stable_content_mapping(self):
        for skill_id, (kind, artifact_type, output_kinds, output_purposes) in EXPECTED.items():
            with self.subTest(skill_id=skill_id):
                directory, contract = load_skill_contract(
                    skill_id,
                    {"skill_directory": str(SKILLS_ROOT / skill_id)},
                )
                self.assertTrue(directory.is_dir())
                self.assertEqual(contract["schema_version"], 2)
                self.assertEqual(contract["produces_context_kind"], kind)
                self.assertEqual(contract["artifact_type"], artifact_type)
                self.assertEqual(contract["artifact_output_kinds"], output_kinds)
                self.assertEqual(contract["artifact_output_purposes"], output_purposes)
                self.assertEqual(contract["language"], "zh-CN")
                self.assertTrue(contract["canonical_document_only"])

    def test_video_contract_consumes_audio_design_as_upstream_context(self):
        payload = json.loads(
            (SKILLS_ROOT / "video-prompt-director" / "agent-contract.json").read_text(encoding="utf-8")
        )
        self.assertIn("audio.design", payload["accepts_context_kinds"])
        self.assertEqual(
            payload["artifact_output_purposes"]["video_prompt"],
            ["segment_execution"],
        )

    def test_script_contract_explicitly_allows_no_prompt_outputs(self):
        payload = json.loads(
            (SKILLS_ROOT / "script-director" / "agent-contract.json").read_text(encoding="utf-8")
        )
        self.assertEqual(payload["artifact_output_kinds"], [])


if __name__ == "__main__":
    unittest.main()
