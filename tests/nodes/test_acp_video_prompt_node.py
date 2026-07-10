import unittest
from unittest.mock import patch

from ryan_comfy_utils.nodes.acp_nodes import (
    DEFAULT_VIDEO_PROMPT_MANIFEST_PATH,
    RyanACPVideoPromptAgent,
)


class TestACPVideoPromptNode(unittest.TestCase):
    def test_contract(self):
        node = RyanACPVideoPromptAgent()
        self.assertEqual(node.RETURN_NAMES, ("response_text", "session_dir", "raw_result_json"))
        optional = RyanACPVideoPromptAgent.INPUT_TYPES()["optional"]
        self.assertIn("image_01", optional)
        self.assertNotIn("image_paths", optional)
        required = RyanACPVideoPromptAgent.INPUT_TYPES()["required"]
        self.assertIn("export_to_file", required)

    @patch("ryan_comfy_utils.nodes.acp_nodes.run_fixed_acp_agent")
    def test_run_text_only(self, run_fixed):
        run_fixed.return_value = ("video prompt", "/tmp/s", "{}")
        node = RyanACPVideoPromptAgent()
        out = node.run(
            user_text="slow dolly forward",
            profile_path="p",
            workspace_root="/tmp/w",
            session_id="s2",
            export_to_file=False,
            manifest_path=str(DEFAULT_VIDEO_PROMPT_MANIFEST_PATH),
        )
        self.assertEqual(out[0], "video prompt")
        kwargs = run_fixed.call_args.kwargs
        self.assertEqual(kwargs["image_paths"], "")


if __name__ == "__main__":
    unittest.main()