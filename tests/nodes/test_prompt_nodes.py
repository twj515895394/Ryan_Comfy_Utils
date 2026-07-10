import unittest
from ryan_comfy_utils.nodes.prompt_nodes import RyanPromptTemplate


class TestPromptNodes(unittest.TestCase):
    def test_input_types(self):
        required = RyanPromptTemplate.INPUT_TYPES()["required"]
        self.assertIn("template_source", required)
        self.assertIn("prompt_dir", required)
        self.assertIn("template_name", required)
        self.assertIn("user_prompt", required)
        self.assertIn("append_user_prompt", required)
        self.assertNotIn("variables_json", required)

    def test_run_built_in_template_no_append(self):
        node = RyanPromptTemplate()
        final, template = node.run(
            template_source="内置模板",
            prompt_dir="",
            template_name="video_frame_analysis.md",
            user_prompt="",
            append_user_prompt=False
        )
        self.assertIn("请基于输入的视频关键帧进行分析。", template)
        self.assertEqual(final, template)

    def test_run_built_in_template_with_append(self):
        node = RyanPromptTemplate()
        final, template = node.run(
            template_source="内置模板",
            prompt_dir="",
            template_name="video_frame_analysis.md",
            user_prompt="Please check context details.",
            append_user_prompt=True
        )
        self.assertTrue(final.endswith("\n\nPlease check context details."))


if __name__ == "__main__":
    unittest.main()
