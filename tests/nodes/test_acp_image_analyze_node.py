import unittest
from unittest.mock import patch

from ryan_comfy_utils.acp.contracts import load_manifest
from ryan_comfy_utils.nodes.acp_nodes import (
    DEFAULT_IMAGE_ANALYZE_MANIFEST_PATH,
    RyanACPImageAnalyzeAgent,
)


class TestACPImageAnalyzeNode(unittest.TestCase):
    def test_manifest_skill(self):
        manifest = load_manifest(DEFAULT_IMAGE_ANALYZE_MANIFEST_PATH)
        self.assertEqual(manifest["skill_id"], "image_prompt_reverse")

    def test_contract_has_category_and_export_toggle(self):
        required = RyanACPImageAnalyzeAgent.INPUT_TYPES()["required"]
        self.assertIn("category", required)
        self.assertIn("export_to_file", required)
        self.assertIn("image_paths", required)

    def test_run_requires_image_paths(self):
        node = RyanACPImageAnalyzeAgent()
        with self.assertRaises(ValueError):
            node.run(
                image_paths="",
                user_text="",
                category="general",
                output_language="bilingual",
                profile_path="p",
                workspace_root="/tmp",
                session_id="s",
                export_to_file=False,
            )

    @patch("ryan_comfy_utils.nodes.acp_nodes.export_prompt_to_file")
    @patch("ryan_comfy_utils.nodes.acp_nodes.run_fixed_acp_agent")
    def test_run_exports_when_toggle_on(self, run_fixed, export_file):
        run_fixed.return_value = ("reversed prompt", "/tmp/s", "{}")
        export_file.return_value = "/out/x.md"
        node = RyanACPImageAnalyzeAgent()
        node.run(
            image_paths="/ref.png",
            user_text="detail",
            category="photography",
            output_language="bilingual",
            profile_path="p",
            workspace_root="/tmp",
            session_id="s",
            export_to_file=True,
        )
        export_file.assert_called_once()
        kwargs = export_file.call_args.kwargs
        self.assertEqual(kwargs["category"], "photography")


if __name__ == "__main__":
    unittest.main()