import json
import tempfile
import unittest
from pathlib import Path

from ryan_comfy_utils.creative_workspace.project_repository import CreativeProjectRepository
from ryan_comfy_utils.creative_workspace.stage_export import parse_stage_export, write_stage_export
from ryan_comfy_utils.nodes.creative_text_selector_node import RyanCreativeTextSelector


class TestCreativeTextSelectorNode(unittest.TestCase):
    def test_selects_plain_item_text(self):
        with tempfile.TemporaryDirectory() as tmp:
            # isolate repository root via monkeypatch-ish: construct node after chdir? 
            # Node uses default CreativeProjectRepository(); point output via env not available.
            # Instead write into default by patching instance repository.
            repo = CreativeProjectRepository(Path(tmp) / "ryan_creative_workspace")
            project = repo.create_project("sel")
            pid = project["project_id"]
            export = {
                "stage_id": "video_prompt",
                "canon_markdown": "# V\n",
                "deliverables": [
                    {
                        "doc_key": "shot_video_prompts",
                        "format": "items",
                        "items": [
                            {"id": "SHOT_003", "label": "推进", "text": "pure video prompt three"},
                        ],
                    }
                ],
            }
            text = f"```ryan-stage-export\n{json.dumps(export, ensure_ascii=False)}\n```"
            write_stage_export(repo, pid, "video_prompt", parse_stage_export(text), revision=1)
            node = RyanCreativeTextSelector()
            node._repository = repo
            from ryan_comfy_utils.creative_workspace.stage_service import CreativeStageService

            node._stage_service = CreativeStageService(repo)
            out = node.select(
                creative_project_id=pid,
                document_path="deliverables/video_prompt/shot_video_prompts.items.md",
                item_id="SHOT_003",
            )
            self.assertEqual(out, ("pure video prompt three",))

    def test_items_without_item_id_fail(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = CreativeProjectRepository(Path(tmp) / "ryan_creative_workspace")
            project = repo.create_project("sel2")
            pid = project["project_id"]
            export = {
                "stage_id": "production",
                "canon_markdown": "# P\n",
                "deliverables": [
                    {
                        "doc_key": "image_prompts",
                        "format": "items",
                        "items": [{"id": "CHAR_1", "label": "c", "text": "x"}],
                    }
                ],
            }
            text = f"```ryan-stage-export\n{json.dumps(export, ensure_ascii=False)}\n```"
            write_stage_export(repo, pid, "production", parse_stage_export(text), revision=1)
            node = RyanCreativeTextSelector()
            node._repository = repo
            from ryan_comfy_utils.creative_workspace.stage_service import CreativeStageService

            node._stage_service = CreativeStageService(repo)
            with self.assertRaises(ValueError):
                node.select(
                    creative_project_id=pid,
                    document_path="deliverables/production/image_prompts.items.md",
                    item_id="",
                )


if __name__ == "__main__":
    unittest.main()
