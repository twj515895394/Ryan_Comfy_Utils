import unittest
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
            "outputs": {"response_text": "hello from node"},
            "session_dir": "/tmp/session_001",
            "raw_result_json": {"returncode": 0, "stdout": "hello from node", "stderr": ""},
        }
        node = RyanACPUniversalAgent()
        response_text, session_dir, raw_result_json = node.run(
            skill_id="video_prompt_generator",
            user_text="describe this clip",
            profile_path="ryan_comfy_utils/acp/fixtures/profiles/local_codex.json",
            manifest_path="ryan_comfy_utils/acp/fixtures/manifests/universal_agent.json",
            workspace_root="/tmp/acp_workspace",
            session_id="session_001",
            skill_root="/tmp/skills",
        )
        self.assertEqual(response_text, "hello from node")
        self.assertEqual(session_dir, "/tmp/session_001")
        self.assertIn("hello from node", raw_result_json)
