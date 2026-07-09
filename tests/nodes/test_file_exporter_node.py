import tempfile
import unittest
from pathlib import Path

from ryan_comfy_utils.acp.file_exporter import write_text_export
from ryan_comfy_utils.nodes.file_nodes import RyanFileExporter


class TestFileExporterNode(unittest.TestCase):
    def test_write_md_with_timestamp(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = write_text_export(
                text="hello prompt",
                output_subdir="ryan_acp_exports/manual",
                filename="note",
                extension="md",
                append_timestamp=False,
                output_root=root,
            )
            self.assertTrue(path.endswith(".md"))
            self.assertIn("hello prompt", Path(path).read_text(encoding="utf-8"))

    def test_overwrite_false_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_text_export(
                text="a",
                extension="txt",
                append_timestamp=False,
                filename="same",
                output_root=root,
            )
            with self.assertRaises(FileExistsError):
                write_text_export(
                    text="b",
                    extension="txt",
                    append_timestamp=False,
                    filename="same",
                    overwrite=False,
                    output_root=root,
                )

    def test_node_contract(self):
        self.assertEqual(RyanFileExporter.RETURN_NAMES, ("file_path", "file_text"))
        self.assertEqual(RyanFileExporter.CATEGORY, "Ryan Utils / File")


if __name__ == "__main__":
    unittest.main()