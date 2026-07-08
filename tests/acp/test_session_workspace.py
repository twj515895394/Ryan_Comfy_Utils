import json
import tempfile
import unittest
from pathlib import Path

from ryan_comfy_utils.acp.session import create_session_record
from ryan_comfy_utils.acp.workspace import prepare_workspace


class TestSessionWorkspace(unittest.TestCase):
    def test_prepare_workspace_creates_expected_directories(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = prepare_workspace(Path(tmpdir), "session_001")
            self.assertTrue((workspace / "input").exists())
            self.assertTrue((workspace / "output").exists())
            self.assertTrue((workspace / "logs").exists())

    def test_create_session_record_writes_metadata_and_context_paths(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = prepare_workspace(Path(tmpdir), "session_001")
            record = create_session_record(
                workspace=workspace,
                runner="codex_cli",
                skill_id="video_prompt_generator",
                context_payload={"input": {"text": "hello"}},
            )
            metadata = json.loads((workspace / "metadata.json").read_text(encoding="utf-8"))
            self.assertEqual(record["skill_id"], "video_prompt_generator")
            self.assertEqual(metadata["runner"], "codex_cli")
            self.assertTrue((workspace / "context.json").exists())
