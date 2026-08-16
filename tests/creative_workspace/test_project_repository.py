import tempfile
import unittest
from pathlib import Path

from ryan_comfy_utils.creative_workspace.project_repository import CreativeProjectRepository


class TestCreativeProjectRepository(unittest.TestCase):
    def test_create_list_open_and_reset_keeps_old_project(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = CreativeProjectRepository(Path(tmp) / "ryan_creative_workspace")
            first = repo.create_project(name="雨夜")
            first_id = first["project_id"]
            self.assertEqual(repo.get_current_project_id(), first_id)
            self.assertTrue((repo.paths(first_id).root / "project.json").is_file())

            second = repo.reset_workspace(name="新作")
            second_id = second["project_id"]
            self.assertNotEqual(first_id, second_id)
            self.assertEqual(repo.get_current_project_id(), second_id)
            self.assertTrue(repo.project_exists(first_id))
            self.assertTrue(repo.project_exists(second_id))

            ids = {row["project_id"] for row in repo.list_projects()}
            self.assertEqual(ids, {first_id, second_id})

            opened = repo.open_project(first_id)
            self.assertEqual(opened["project_id"], first_id)
            self.assertEqual(repo.get_current_project_id(), first_id)

    def test_rejects_path_escape_project_id(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = CreativeProjectRepository(Path(tmp) / "ryan_creative_workspace")
            with self.assertRaises(ValueError):
                repo.paths("../escape")


if __name__ == "__main__":
    unittest.main()
