import tempfile
import unittest
from pathlib import Path

from ryan_comfy_utils.acp.file_exporter import (
    NODE_SLUG_IMAGE_ANALYZE,
    build_export_path,
    export_prompt_to_file,
    format_export_markdown,
)


class TestFileExporter(unittest.TestCase):
    def test_build_export_path_uses_node_slug(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = build_export_path(root, NODE_SLUG_IMAGE_ANALYZE, "session_x", "")
            self.assertIn("ryan_acp_exports", str(path))
            self.assertIn("image_analyze", str(path))
            self.assertTrue(path.name.endswith(".md"))

    def test_export_prompt_writes_markdown(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            out = export_prompt_to_file(
                response_text="hello prompt",
                node_name="Ryan Image Analyze Agent",
                node_slug=NODE_SLUG_IMAGE_ANALYZE,
                session_id="s1",
                category="general",
                output_root=root,
            )
            text = Path(out).read_text(encoding="utf-8")
            self.assertIn("hello prompt", text)
            self.assertIn("category: general", text)

    def test_format_export_markdown_frontmatter(self):
        md = format_export_markdown(
            "body",
            node_name="N",
            node_slug="image_analyze",
            session_id="s",
        )
        self.assertTrue(md.startswith("---"))


if __name__ == "__main__":
    unittest.main()