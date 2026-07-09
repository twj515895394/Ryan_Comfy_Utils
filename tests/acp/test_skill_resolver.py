import tempfile
import unittest
from pathlib import Path

from ryan_comfy_utils.acp.skill_resolver import resolve_skill_binding


class TestSkillResolver(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "my_skill").mkdir()
        (self.root / "user_skill").mkdir()

    def tearDown(self):
        self.tmp.cleanup()

    def test_fixed_ignores_user_skill_id(self):
        manifest = {"skill_id": "my_skill", "mode": "fixed"}
        binding = resolve_skill_binding(
            manifest,
            str(self.root),
            user_skill_id="user_skill",
            allow_user_skill=False,
        )
        self.assertEqual(binding.skill_id, "my_skill")
        self.assertEqual(binding.source, "manifest")
        self.assertEqual(binding.mode, "fixed")

    def test_selectable_prefers_user(self):
        manifest = {"skill_id": "my_skill", "mode": "selectable"}
        binding = resolve_skill_binding(
            manifest,
            str(self.root),
            user_skill_id="user_skill",
            allow_user_skill=True,
        )
        self.assertEqual(binding.skill_id, "user_skill")
        self.assertEqual(binding.source, "user_input")

    def test_selectable_fallback_manifest(self):
        manifest = {"skill_id": "my_skill", "mode": "selectable"}
        binding = resolve_skill_binding(
            manifest,
            str(self.root),
            user_skill_id="",
            allow_user_skill=True,
        )
        self.assertEqual(binding.skill_id, "my_skill")
        self.assertEqual(binding.source, "manifest")

    def test_skill_dir_exists(self):
        manifest = {"skill_id": "my_skill"}
        binding = resolve_skill_binding(manifest, str(self.root), allow_user_skill=False)
        self.assertTrue(binding.skill_dir.is_dir())


if __name__ == "__main__":
    unittest.main()