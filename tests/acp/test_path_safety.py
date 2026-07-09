import tempfile
import unittest
from pathlib import Path

from ryan_comfy_utils.acp.path_safety import (
    resolve_under_root,
    sanitize_path_component,
    sanitize_relative_subdir,
)


class TestPathSafety(unittest.TestCase):
    def test_sanitize_accepts_safe_names(self):
        self.assertEqual(sanitize_path_component("session_01"), "session_01")
        self.assertEqual(sanitize_path_component("image_prompt"), "image_prompt")

    def test_sanitize_rejects_traversal(self):
        with self.assertRaises(ValueError):
            sanitize_path_component("..")
        with self.assertRaises(ValueError):
            sanitize_path_component("../etc")
        with self.assertRaises(ValueError):
            sanitize_path_component("a/b")
        with self.assertRaises(ValueError):
            sanitize_path_component("")

    def test_sanitize_relative_subdir(self):
        self.assertEqual(
            sanitize_relative_subdir("ryan_acp_exports/manual"),
            "ryan_acp_exports/manual",
        )
        with self.assertRaises(ValueError):
            sanitize_relative_subdir("../etc")

    def test_resolve_under_root_blocks_escape(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ok = resolve_under_root(root, "a", "b.txt")
            self.assertTrue(str(ok).startswith(str(root.resolve())))
            with self.assertRaises(ValueError):
                resolve_under_root(root, "..", "etc")


if __name__ == "__main__":
    unittest.main()
