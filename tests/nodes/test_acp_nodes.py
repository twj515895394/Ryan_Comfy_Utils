import unittest
import tempfile
import json
from pathlib import Path
from unittest.mock import patch

from ryan_comfy_utils.nodes.acp_nodes import RyanACPUniversalAgent


class TestACPNode(unittest.TestCase):
    def test_node_returns_text_contract_outputs(self):
        node = RyanACPUniversalAgent()
        self.assertEqual(node.RETURN_TYPES, ("STRING", "STRING", "STRING"))
        self.assertEqual(
            node.RETURN_NAMES,
            ("response_text", "session_dir", "raw_result_json"),
        )

    @patch("ryan_comfy_utils.nodes.acp_nodes.execute_text_session")
    def test_node_run_returns_runtime_outputs(self, execute_text_session):
        execute_text_session.return_value = {
            "outputs": {"answer_text": "hello from node"},
            "session_dir": "/tmp/session_001",
            "raw_result_json": {"returncode": 0, "stdout": "hello from node", "stderr": ""},
        }
        with tempfile.TemporaryDirectory() as tmpdir:
            skill_root = Path(tmpdir) / "skills"
            (skill_root / "video_prompt_generator").mkdir(parents=True)
            manifest_path = Path(tmpdir) / "manifest.json"
            manifest_path.write_text(
                json.dumps(
                    {
                        "node_id": "ryan.acp.universal_agent",
                        "skill_id": "video_prompt_generator",
                        "mode": "selectable",
                        "context_template": "用户输入:\\n{input.text}",
                        "input_contract": {"text": True, "images": False, "files": False},
                        "output_contract": {
                            "type": "text",
                            "fields": ["response_text", "raw_result_json"],
                        },
                        "result_mapping": {
                            "response_text": "outputs.answer_text",
                            "raw_result_json": "raw_result_json",
                        },
                    }
                ),
                encoding="utf-8",
            )
            node = RyanACPUniversalAgent()
            response_text, session_dir, raw_result_json = node.run(
                skill_id="video_prompt_generator",
                user_text="describe this clip",
                profile_path="ryan_comfy_utils/acp/fixtures/profiles/local_codex.json",
                manifest_path=str(manifest_path),
                workspace_root="/tmp/acp_workspace",
                session_id="session_001",
                skill_root=str(skill_root),
            )
            execute_text_session.assert_called_once()
            call_kw = execute_text_session.call_args.kwargs
            self.assertEqual(call_kw["skill_id"], "video_prompt_generator")
            self.assertEqual(response_text, "hello from node")
            self.assertEqual(session_dir, "/tmp/session_001")
            self.assertIn("hello from node", raw_result_json)
