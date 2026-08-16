import unittest

from ryan_comfy_utils.workflow_agent.context_select import ContextViewPolicy, render_context_view
from ryan_comfy_utils.workflow_agent.models import RyanContext, RyanContextEntry


class TestContextView(unittest.TestCase):
    def _entry(self, entry_id, agent_uid, kind, revision, summary, content, metadata=None):
        return RyanContextEntry(
            entry_id=entry_id,
            workflow_id="wf_view",
            source_agent_uid=agent_uid,
            source_agent_name=agent_uid,
            kind=kind,
            revision=revision,
            summary=summary,
            content=content,
            metadata=metadata or {},
        )

    def test_summary_uses_latest_revision_and_avoids_full_body(self):
        context = RyanContext(
            workflow_id="wf_view",
            entries=[
                self._entry("old", "agent_story", "creative.story", 1, "old summary", "OLD BODY"),
                self._entry("new", "agent_story", "creative.story", 2, "new summary", "NEW BODY"),
                self._entry("art", "agent_art", "production.design", 1, "design summary", "DESIGN BODY"),
            ],
        )
        result = render_context_view(context, ["creative.story"], mode="summary")
        self.assertIn("new summary", result)
        self.assertNotIn("OLD BODY", result)
        self.assertNotIn("NEW BODY", result)
        self.assertIn("design summary", result)
        self.assertEqual(len(context.entries), 3)

    def test_selected_mode_returns_only_requested_output(self):
        context = RyanContext(
            workflow_id="wf_view",
            entries=[
                self._entry(
                    "art",
                    "agent_art",
                    "production.design",
                    1,
                    "summary",
                    "body",
                    {
                        "artifact_bundle": {
                            "artifact_type": "production_design",
                            "content": {},
                            "outputs": [
                                {"output_id": "image_01", "kind": "image_prompt", "label": "主视觉", "text": "IMAGE"},
                                {"output_id": "image_02", "kind": "image_prompt", "label": "备选", "text": "OTHER"},
                            ],
                        }
                    },
                )
            ],
        )
        result = render_context_view(context, ["production.design"], mode="selected", selected_output_ids=["image_01"])
        self.assertIn("IMAGE", result)
        self.assertNotIn("OTHER", result)
        self.assertNotIn("body", result)


    def test_summary_renders_handoff_and_locks_without_unselected_prompt(self):
        context = RyanContext(
            workflow_id="wf_view",
            entries=[
                self._entry(
                    "art_v2",
                    "agent_art",
                    "production.design",
                    2,
                    "legacy summary",
                    "FULL CANON BODY",
                    {
                        "artifact_bundle": {
                            "artifact_type": "production_design",
                            "schema_version": 2,
                            "content": {
                                "summary": "角色锁",
                                "handoff": "交给分镜",
                                "locks": ["CHAR_001", "SCENE_001"],
                            },
                            "outputs": [
                                {
                                    "output_id": "CHAR_001_REFERENCE",
                                    "kind": "image_prompt",
                                    "label": "CHAR_001 · 角色说明书板",
                                    "purpose": "character_sheet",
                                    "target_ids": ["CHAR_001"],
                                    "text": "中文角色参考图 Prompt",
                                }
                            ],
                            "shots": [],
                        }
                    },
                )
            ],
        )
        result = render_context_view(context, ["production.design"], mode="summary")
        self.assertIn("角色锁", result)
        self.assertIn("交给分镜", result)
        self.assertIn("CHAR_001", result)
        self.assertNotIn("中文角色参考图 Prompt", result)
    def test_total_budget_reports_omitted_sources(self):
        context = RyanContext(
            workflow_id="wf_view",
            entries=[
                self._entry("one", "agent_one", "creative.story", 1, "A" * 40, "body"),
                self._entry("two", "agent_two", "production.design", 1, "B" * 40, "body"),
                self._entry("three", "agent_three", "storyboard.plan", 1, "C" * 40, "body"),
            ],
        )
        result = render_context_view(
            context,
            ["*"],
            policy=ContextViewPolicy(source_limit=100, total_limit=180),
        )
        self.assertLessEqual(len(result), 300)
        self.assertIn("[Context truncated]", result)
        self.assertIn("omitted=", result)


if __name__ == "__main__":
    unittest.main()
