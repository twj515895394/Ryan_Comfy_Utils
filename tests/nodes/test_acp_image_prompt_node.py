import unittest
from unittest.mock import patch

from ryan_comfy_utils.nodes.acp_nodes import (
    DEFAULT_IMAGE_PROMPT_MANIFEST_PATH,
    RyanACPImagePromptAgent,
)


class TestACPImagePromptNode(unittest.TestCase):
    def test_contract(self):
        node = RyanACPImagePromptAgent()
        self.assertEqual(node.RETURN_NAMES, ("response_text", "session_dir", "raw_result_json"))
        required = RyanACPImagePromptAgent.INPUT_TYPES()["required"]
        self.assertIn("user_text", required)
        optional = RyanACPImagePromptAgent.INPUT_TYPES()["optional"]
        self.assertIn("image_paths", optional)
        self.assertIn("style", optional)

    @patch("ryan_comfy_utils.nodes.acp_nodes.run_fixed_acp_agent")
    def test_run_forwards_to_fixed_runner(self, run_fixed):
        run_fixed.return_value = ("img prompt", "/tmp/s", "{}")
        node = RyanACPImagePromptAgent()
        out = node.run(
            user_text="sunset city",
            profile_path="p",
            workspace_root="/tmp/w",
            session_id="s1",
            image_paths="/a.png",
            style="cyberpunk",
            subject="",
            scene="",
            extra_prompt="",
            skill_root="",
            manifest_path=str(DEFAULT_IMAGE_PROMPT_MANIFEST_PATH),
        )
        self.assertEqual(out[0], "img prompt")
        run_fixed.assert_called_once()
        kwargs = run_fixed.call_args.kwargs
        self.assertIn("cyberpunk", kwargs["extra_user_lines"])
        self.assertEqual(kwargs["image_paths"], "/a.png")


if __name__ == "__main__":
    unittest.main()