import json
import unittest

from ryan_comfy_utils.workflow_agent.artifacts import (
    artifact_outputs,
    artifact_shots,
    parse_artifact_markdown,
)
from ryan_comfy_utils.workflow_agent.models import RyanContextEntry


class TestWorkflowAgentArtifacts(unittest.TestCase):
    def _entry(self, metadata):
        return RyanContextEntry(
            entry_id="entry_artifact",
            workflow_id="wf_artifact",
            source_agent_uid="agent_artifact",
            kind="production.design",
            revision=1,
            content="# Design",
            metadata=metadata,
        )

    def test_valid_block_is_extracted_and_cleaned(self):
        text = (
            "# Canonical\n\n正文\n\n"
            "```ryan-artifact\n"
            '{"artifact_type":"production_design","schema_version":1,'
            '"content":{"summary":"人物与场景摘要"},"outputs":['
            '{"output_id":"image_01","kind":"image_prompt","label":"主视觉",'
            '"text":"cinematic portrait","priority":10}],"shots":[]}'
            "\n```\n"
        )
        result = parse_artifact_markdown(text, expected_artifact_type="production_design")
        self.assertEqual(result.status, "valid")
        self.assertEqual(result.cleaned_text, "# Canonical\n\n正文")
        self.assertEqual(result.bundle.outputs[0].output_id, "image_01")
        self.assertEqual(result.bundle.content["summary"], "人物与场景摘要")

    def test_absent_block_preserves_legacy_markdown(self):
        text = "# Legacy\n\n只有旧正文"
        result = parse_artifact_markdown(text, expected_artifact_type="production_design")
        self.assertEqual(result.status, "absent")
        self.assertEqual(result.cleaned_text, text)
        self.assertIsNone(result.bundle)

    def test_invalid_json_preserves_original_markdown(self):
        text = "# Canonical\n\n```ryan-artifact\n{not-json}\n```"
        result = parse_artifact_markdown(text)
        self.assertEqual(result.status, "invalid")
        self.assertEqual(result.cleaned_text, text)
        self.assertIn("Expecting", result.error)

    def test_wrong_type_and_duplicate_output_are_rejected(self):
        wrong = (
            "```ryan-artifact\n"
            '{"artifact_type":"other","schema_version":1,"content":{},"outputs":[]}'
            "\n```"
        )
        self.assertEqual(
            parse_artifact_markdown(wrong, expected_artifact_type="production_design").status,
            "invalid",
        )
        duplicate_text = (
            "```ryan-artifact\n"
            '{"artifact_type":"production_design","schema_version":1,"content":{},"outputs":['
            '{"output_id":"same","kind":"image_prompt","label":"A","text":"a"},'
            '{"output_id":"same","kind":"image_prompt","label":"B","text":"b"}]}'
            "\n```"
        )
        self.assertEqual(parse_artifact_markdown(duplicate_text).status, "invalid")

    def test_artifact_outputs_only_returns_valid_metadata(self):
        entry = self._entry(
            {
                "artifact_bundle": {
                    "artifact_type": "production_design",
                    "content": {},
                    "outputs": [
                        {"output_id": "prompt", "kind": "image_prompt", "label": "Prompt", "text": "a prompt"}
                    ],
                }
            }
        )
        self.assertEqual([item.output_id for item in artifact_outputs(entry)], ["prompt"])
        self.assertEqual(artifact_outputs(self._entry({})), [])

    def test_legacy_fields_are_normalized_to_v1_bundle(self):
        text = (
            "# Legacy Canon\n\n"
            "```ryan-artifact\n"
            '{"artifact_type":"production_design","revision":2,"title":"Legacy",'
            '"summary":"old summary","outputs":['
            '{"kind":"image_prompt","id":"P01","role":"主视觉","prompt":"IMAGE"},'
            '{"kind":"continuity_constraint","id":"LOCK_01","constraint":"LOCK"}],'
            '"shots":[{"id":"SHOT_01","role":"镜头一","prompt":"SHOT"}]}'
            "\n```\n"
        )

        result = parse_artifact_markdown(text, expected_artifact_type="production_design")

        self.assertEqual(result.status, "valid")
        self.assertEqual(result.bundle.outputs[0].to_dict()["output_id"], "P01")
        self.assertEqual(result.bundle.outputs[0].to_dict()["text"], "IMAGE")
        self.assertEqual(result.bundle.outputs[0].to_dict()["label"], "主视觉")
        self.assertEqual(result.bundle.outputs[1].to_dict()["text"], "LOCK")
        self.assertEqual(result.bundle.shots[0].to_dict()["shot_id"], "SHOT_01")
        self.assertEqual(result.bundle.shots[0].prompt, "SHOT")
        self.assertEqual(result.bundle.content["revision"], 2)

    def test_legacy_bundle_in_entry_content_is_read_when_metadata_is_invalid(self):
        content = (
            "# Legacy Canon\n\n```ryan-artifact\n"
            '{"artifact_type":"production_design","revision":2,"outputs":['
            '{"kind":"image_prompt","id":"P01","role":"主视觉","prompt":"IMAGE"}]}'
            "\n```\n"
        )
        entry = self._entry(
            {
                "artifact_status": "invalid",
                "artifact_error": "output_id must be a non-empty path component",
            }
        )
        entry.content = content

        self.assertEqual([item.text for item in artifact_outputs(entry)], ["IMAGE"])
        self.assertEqual(artifact_shots(entry), [])

    def test_v2_prompt_requires_single_chinese_text_and_target_metadata(self):
        text = (
            "正文\n\n```ryan-artifact\n"
            '{"artifact_type":"production_design","schema_version":2,'
            '"content":{"summary":"角色锁","handoff":"交给分镜","locks":["CHAR_001"]},'
            '"outputs":[{"output_id":"CHAR_001_REFERENCE","kind":"image_prompt",'
            '"label":"CHAR_001 · 角色说明书板","purpose":"character_sheet",'
            '"target_ids":["CHAR_001"],"text":"中文角色参考图 Prompt",'
            '"negative_constraints":["不要海报构图"],"aspect_ratio":"4:3"}],"shots":[]}'
            "\n```\n"
        )
        result = parse_artifact_markdown(text)
        self.assertEqual(result.status, "valid")
        self.assertEqual(result.bundle.outputs[0].purpose, "character_sheet")
        self.assertEqual(result.bundle.outputs[0].target_ids, ["CHAR_001"])

    def test_v2_rejects_missing_prompt_purpose_or_targets(self):
        for field in ("purpose", "target_ids"):
            with self.subTest(field=field):
                output = {
                    "output_id": "P01",
                    "kind": "image_prompt",
                    "label": "图",
                    "text": "中文",
                    "purpose": "scene_reference",
                    "target_ids": ["SCENE_001"],
                }
                output.pop(field)
                text = (
                    "```ryan-artifact\n"
                    '{"artifact_type":"production_design","schema_version":2,'
                    '"content":{"summary":"摘要","handoff":"交接","locks":["SCENE_001"]},'
                    f'"outputs":[{json.dumps(output, ensure_ascii=False)}],"shots":[]}}\n'
                    "```"
                )
                result = parse_artifact_markdown(text)
                self.assertEqual(result.status, "invalid")
                self.assertIn(field, result.error)

    def test_v2_script_bundle_allows_empty_outputs(self):
        text = (
            "```ryan-artifact\n"
            '{"artifact_type":"script_direction","schema_version":2,'
            '"content":{"summary":"剧本依据","handoff":"交给分镜","locks":["SCENE_001"]},'
            '"outputs":[],"shots":[]}\n```'
        )
        result = parse_artifact_markdown(
            text,
            expected_artifact_type="script_direction",
            allowed_output_kinds=(),
        )
        self.assertEqual(result.status, "valid")
        self.assertEqual(result.bundle.outputs, [])

    def test_v2_rejects_duplicate_output_ids(self):
        text = (
            "```ryan-artifact\n"
            '{"artifact_type":"production_design","schema_version":2,'
            '"content":{"summary":"摘要","handoff":"交接","locks":["CHAR_001"]},'
            '"outputs":['
            '{"output_id":"P01","kind":"image_prompt","label":"甲","purpose":"character_sheet",'
            '"target_ids":["CHAR_001"],"text":"一"},'
            '{"output_id":"P01","kind":"image_prompt","label":"乙","purpose":"character_sheet",'
            '"target_ids":["CHAR_001"],"text":"二"}],"shots":[]}\n```'
        )
        self.assertEqual(parse_artifact_markdown(text).status, "invalid")

    def test_v2_rejects_bilingual_prompt_fields(self):
        text = (
            "```ryan-artifact\n"
            '{"artifact_type":"production_design","schema_version":2,'
            '"content":{"summary":"摘要","handoff":"交接","locks":["SCENE_001"]},'
            '"outputs":[{"output_id":"P01","kind":"image_prompt","label":"图","purpose":"scene_reference",'
            '"target_ids":["SCENE_001"],"text":"中文","prompt_en":"english"}],"shots":[]}'
            "\n```"
        )
        result = parse_artifact_markdown(text)
        self.assertEqual(result.status, "invalid")
        self.assertIn("bilingual", result.error)

    def test_stage_contract_rejects_unmapped_prompt_kind(self):
        text = (
            "正文\n\n```ryan-artifact\n"
            '{"artifact_type":"script_direction","schema_version":2,'
            '"content":{"summary":"剧本","handoff":"交给分镜","locks":["SCENE_001"]},'
            '"outputs":[{"output_id":"bad","kind":"video_prompt","label":"视频",'
            '"purpose":"segment_execution","target_ids":["SEG_001"],"text":"视频提示"}],'
            '"shots":[]}\n```'
        )
        result = parse_artifact_markdown(
            text,
            expected_artifact_type="script_direction",
            allowed_output_kinds=(),
        )
        self.assertEqual(result.status, "invalid")
        self.assertIn("video_prompt", result.error)
    def test_stage_contract_rejects_unmapped_prompt_purpose(self):
        text = (
            "```ryan-artifact\n"
            '{"artifact_type":"production_design","schema_version":2,'
            '"content":{"summary":"美术","handoff":"交给分镜","locks":["CHAR_001"]},'
            '"outputs":[{"output_id":"CHAR_001_REFERENCE","kind":"image_prompt","label":"角色",'
            '"purpose":"segment_execution","target_ids":["CHAR_001"],"text":"中文参考图"}],'
            '"shots":[]}\n```'
        )
        result = parse_artifact_markdown(
            text,
            expected_artifact_type="production_design",
            allowed_output_kinds=("image_prompt",),
            allowed_output_purposes={
                "image_prompt": ("character_sheet", "character_reference"),
            },
        )
        self.assertEqual(result.status, "invalid")
        self.assertIn("segment_execution", result.error)


    def test_v1_legacy_kind_remains_readable_under_stage_filter(self):
        text = (
            "```ryan-artifact\n"
            '{"artifact_type":"production_design","revision":3,"outputs":['
            '{"kind":"continuity_constraint","id":"LOCK_STYLE","constraint":"锁定写实风格"},'
            '{"kind":"image_prompt","id":"CHAR_001_REFERENCE","role":"角色参考","prompt":"角色图"}],'
            '"shots":[]}\n```'
        )
        result = parse_artifact_markdown(
            text,
            expected_artifact_type="production_design",
            allowed_output_kinds=("image_prompt",),
        )
        self.assertEqual(result.status, "valid")
        self.assertEqual(
            [output.kind for output in result.bundle.outputs],
            ["continuity_constraint", "image_prompt"],
        )

    def test_explicit_future_schema_version_remains_invalid(self):
        text = (
            "```ryan-artifact\n"
            '{"artifact_type":"production_design","schema_version":3,'
            '"content":{},"outputs":[],"shots":[]}'
            "\n```"
        )

        result = parse_artifact_markdown(text)
        self.assertEqual(result.status, "invalid")
        self.assertIn("schema_version must be 1 or 2", result.error)

    def test_v2_sanitizes_scalar_reference_role_values_without_losing_prompt(self):
        text = (
            "```ryan-artifact\n"
            '{"artifact_type":"production_design","schema_version":2,'
            '"content":{"summary":"摘要","handoff":"交接","locks":["CHAR_001"]},'
            '"outputs":[{"output_id":"P01","kind":"image_prompt","label":"角色",'
            '"purpose":"character_sheet","target_ids":["CHAR_001"],"text":"中文",'
            '"reference_roles":{"IDENTITY_REFERENCE":"南城 华强.png"}}],"shots":[]}\n```'
        )
        result = parse_artifact_markdown(text)
        self.assertEqual(result.status, "valid")
        self.assertEqual(result.bundle.outputs[0].reference_roles, {})
        self.assertEqual(result.bundle.outputs[0].text, "中文")

    def test_v2_rejects_non_string_scalar_reference_role_values(self):
        text = (
            "```ryan-artifact\n"
            '{"artifact_type":"production_design","schema_version":2,'
            '"content":{"summary":"摘要","handoff":"交接","locks":["CHAR_001"]},'
            '"outputs":[{"output_id":"P01","kind":"image_prompt","label":"角色",'
            '"purpose":"character_sheet","target_ids":["CHAR_001"],"text":"中文",'
            '"reference_roles":{"IDENTITY_REFERENCE":123}}],"shots":[]}\n```'
        )
        result = parse_artifact_markdown(text)
        self.assertEqual(result.status, "invalid")
        self.assertIn("reference_roles must contain arrays", result.error)

    def test_v2_accepts_array_reference_role_values(self):
        text = (
            "```ryan-artifact\n"
            '{"artifact_type":"production_design","schema_version":2,'
            '"content":{"summary":"摘要","handoff":"交接","locks":["CHAR_001"]},'
            '"outputs":[{"output_id":"P01","kind":"image_prompt","label":"角色",'
            '"purpose":"character_sheet","target_ids":["CHAR_001"],"text":"中文",'
            '"reference_roles":{"IDENTITY_REFERENCE":["asset_id"]}}],"shots":[]}\n```'
        )
        result = parse_artifact_markdown(text)
        self.assertEqual(result.status, "valid")
        self.assertEqual(
            result.bundle.outputs[0].reference_roles,
            {"IDENTITY_REFERENCE": ["asset_id"]},
        )


if __name__ == "__main__":
    unittest.main()
