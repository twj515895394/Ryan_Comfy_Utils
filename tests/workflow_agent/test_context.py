import unittest

from ryan_comfy_utils.workflow_agent.context_merge import (
    ContextConflict,
    WorkflowContextMismatch,
    append_commit,
    merge_contexts,
)
from ryan_comfy_utils.workflow_agent.context_select import select_context_entries
from ryan_comfy_utils.workflow_agent.models import (
    RyanAssetRef,
    RyanContext,
    RyanContextEntry,
    RyanContextLineage,
)


class TestWorkflowAgentContext(unittest.TestCase):
    def setUp(self):
        self.workflow_id = "wf_context"
        self.entry = RyanContextEntry(
            entry_id="entry_story_v1",
            workflow_id=self.workflow_id,
            source_agent_uid="agent_story",
            source_agent_name="Story Agent",
            skill_id="script-director",
            kind="script.direction",
            revision=1,
            content="# Story",
            created_at="2026-08-10T10:00:00Z",
        )
        self.asset = RyanAssetRef(
            asset_id="asset_reference",
            workflow_id=self.workflow_id,
            type="image",
            mime_type="image/png",
            uri="assets/reference.png",
        )

    def test_merge_deduplicates_entries_assets_and_lineage(self):
        lineage = RyanContextLineage(
            lineage_id="lineage_story",
            workflow_id=self.workflow_id,
            entry_id=self.entry.entry_id,
        )
        left = RyanContext(
            workflow_id=self.workflow_id,
            entries=[self.entry],
            assets=[self.asset],
            lineage=[lineage],
        )
        right = RyanContext(
            workflow_id=self.workflow_id,
            entries=[self.entry],
            assets=[self.asset],
            lineage=[lineage],
        )

        merged = merge_contexts([left, right])

        self.assertEqual([item.entry_id for item in merged.entries], [self.entry.entry_id])
        self.assertEqual([item.asset_id for item in merged.assets], [self.asset.asset_id])
        self.assertEqual([item.lineage_id for item in merged.lineage], [lineage.lineage_id])
        self.assertEqual(left.entries[0].content, "# Story")

    def test_merge_rejects_cross_workflow_and_same_id_conflict(self):
        other = RyanContextEntry(
            entry_id=self.entry.entry_id,
            workflow_id=self.workflow_id,
            source_agent_uid="agent_story",
            kind="script.direction",
            revision=2,
            content="# Conflicting story",
        )
        with self.assertRaises(WorkflowContextMismatch):
            merge_contexts([RyanContext(self.workflow_id), RyanContext("wf_other")])
        with self.assertRaises(ContextConflict):
            merge_contexts(
                [
                    RyanContext(self.workflow_id, entries=[self.entry]),
                    RyanContext(self.workflow_id, entries=[other]),
                ]
            )

    def test_selector_keeps_latest_revision_and_prioritizes_accepted_kind(self):
        latest = RyanContextEntry(
            entry_id="entry_story_v2",
            workflow_id=self.workflow_id,
            source_agent_uid="agent_story",
            kind="script.direction",
            revision=2,
            content="# Updated Story",
        )
        review = RyanContextEntry(
            entry_id="entry_review_v1",
            workflow_id=self.workflow_id,
            source_agent_uid="agent_review",
            kind="review.report",
            revision=1,
            content="Review",
        )
        selected = select_context_entries(
            RyanContext(self.workflow_id, entries=[self.entry, latest, review]),
            ["script.direction"],
        )

        self.assertEqual([item.entry_id for item in selected], [latest.entry_id, review.entry_id])

    def test_append_commit_creates_canonical_entry(self):
        result = append_commit(
            None,
            {
                "entry_id": "entry_commit",
                "workflow_id": self.workflow_id,
                "source_agent_uid": "agent_story",
                "kind": "script.direction",
                "revision": 1,
                "content": "Canonical",
            },
            workflow_id=self.workflow_id,
        )

        self.assertEqual(result.entries[0].entry_id, "entry_commit")
        self.assertEqual(result.entries[0].content, "Canonical")
        self.assertTrue(result.lineage)

    def test_append_commit_normalizes_legacy_artifact_for_downstream_context(self):
        legacy = (
            "# Production Design Canon\n\n```ryan-artifact\n"
            '{"artifact_type":"production_design","revision":2,"outputs":['
            '{"kind":"image_prompt","id":"P01","role":"主视觉","prompt":"IMAGE"}]}'
            "\n```\n"
        )
        result = append_commit(
            None,
            {
                "entry_id": "entry_legacy",
                "workflow_id": self.workflow_id,
                "source_agent_uid": "agent_design",
                "kind": "production.design",
                "revision": 2,
                "content": legacy,
                "metadata": {
                    "artifact_status": "invalid",
                    "artifact_error": "output_id must be a non-empty path component",
                },
            },
            workflow_id=self.workflow_id,
        )

        entry = result.entries[0]
        self.assertEqual(entry.metadata["artifact_status"], "valid")
        self.assertEqual(entry.metadata["artifact_bundle"]["outputs"][0]["output_id"], "P01")
        self.assertEqual(entry.content, "# Production Design Canon")

    def test_context_does_not_accept_chat_history(self):
        with self.assertRaises(ValueError):
            RyanContext.from_dict(
                {
                    "schema_version": 1,
                    "workflow_id": self.workflow_id,
                    "entries": [],
                    "assets": [],
                    "lineage": [],
                    "metadata": {},
                    "chat_history": [{"role": "user", "content": "draft"}],
                }
            )


if __name__ == "__main__":
    unittest.main()
