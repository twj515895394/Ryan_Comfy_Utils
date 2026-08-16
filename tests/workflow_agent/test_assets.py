import tempfile
import unittest
from pathlib import Path

from ryan_comfy_utils.workflow_agent.assets import (
    MAX_ASSET_BYTES,
    AssetNotFoundError,
    AssetStoreError,
    WorkflowAgentAssetStore,
)
from ryan_comfy_utils.workflow_agent.repository import WorkflowAgentRepository


class TestWorkflowAgentAssetStore(unittest.TestCase):
    def make_store(self, tmp: str) -> WorkflowAgentAssetStore:
        return WorkflowAgentAssetStore(WorkflowAgentRepository(Path(tmp) / "acp_workspace"))

    def test_attach_copies_file_and_deduplicates_stably(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "reference.png"
            source.write_bytes(b"png bytes")
            store = self.make_store(tmp)
            first = store.attach("wf_one", "agent_one", source, source="node_input")
            second = store.attach("wf_one", "agent_one", source, source="chat_upload")

            self.assertEqual(first.asset_id, second.asset_id)
            self.assertEqual(first.source, "node_input")
            self.assertEqual(first.mime_type, "image/png")
            self.assertNotEqual(Path(first.uri).resolve(), source.resolve())
            self.assertTrue(Path(first.uri).is_file())
            self.assertEqual(len(store.list("wf_one", "agent_one")), 1)

    def test_text_extraction_reports_context_truncation(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "notes.md"
            source.write_text("a" * 120_000, encoding="utf-8")
            store = self.make_store(tmp)
            ref = store.attach("wf_one", "agent_one", source)
            result = store.extract_text(ref)

            self.assertEqual(len(result["text"]), 100_000)
            self.assertTrue(result["truncated"])
            self.assertIn("truncated", result["message"])
            self.assertEqual(result["original_chars"], 120_000)

    def test_invalid_missing_and_oversized_files_are_readable_errors(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = self.make_store(tmp)
            with self.assertRaisesRegex(AssetStoreError, "does not exist"):
                store.attach("wf_one", "agent_one", Path(tmp) / "missing.txt")
            oversized = Path(tmp) / "large.txt"
            with oversized.open("wb") as handle:
                handle.truncate(MAX_ASSET_BYTES + 1)
            with self.assertRaisesRegex(AssetStoreError, "maximum size"):
                store.attach("wf_one", "agent_one", oversized)

    def test_audio_is_recognized_but_disabled(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "voice.mp3"
            source.write_bytes(b"not audio")
            with self.assertRaisesRegex(AssetStoreError, "audio.*disabled"):
                self.make_store(tmp).attach("wf_one", "agent_one", source)

    def test_detach_only_removes_scope_reference_and_keeps_copy(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "data.csv"
            source.write_text("a,b\n1,2\n", encoding="utf-8")
            store = self.make_store(tmp)
            ref = store.attach("wf_one", "agent_one", source)
            store.detach("wf_one", "agent_one", ref.asset_id)
            self.assertEqual(store.list("wf_one", "agent_one"), [])
            self.assertTrue(Path(ref.uri).is_file())
            with self.assertRaises(AssetNotFoundError):
                store.get("wf_one", "agent_one", ref.asset_id)
    def test_prepare_context_resolves_asset_from_upstream_scope(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "brief.md"
            source.write_text("# brief\n", encoding="utf-8")
            store = self.make_store(tmp)
            ref = store.attach("wf_one", "source_agent", source, source="node_input")

            prepared = store.prepare_context("wf_one", "downstream_agent", [ref.to_dict()])

            self.assertEqual([item["asset_id"] for item in prepared["refs"]], [ref.asset_id])
            self.assertEqual(prepared["documents"][0]["text"], "# brief\n")


    def test_video_without_valid_frames_returns_explicit_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "clip.mp4"
            source.write_bytes(b"invalid video")
            with self.assertRaisesRegex(AssetStoreError, "video (dependency unavailable|has no valid)"):
                self.make_store(tmp).attach("wf_one", "agent_one", source)


if __name__ == "__main__":
    unittest.main()
