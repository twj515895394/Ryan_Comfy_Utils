import json
import tempfile
import unittest
from pathlib import Path

from ryan_comfy_utils.creative_workspace.project_repository import CreativeProjectRepository
from ryan_comfy_utils.creative_workspace.stage_export import (
    StageExportError,
    check_ready,
    list_project_documents,
    parse_items_markdown,
    parse_stage_export,
    select_document_or_item,
    write_stage_export,
)
from ryan_comfy_utils.creative_workspace.stage_registry import load_pipeline
from ryan_comfy_utils.creative_workspace.stage_service import CreativeStageService


def _export_text(stage_id: str, items: list[dict], canon: str = "# Canon\nbody\n") -> str:
    payload = {
        "stage_id": stage_id,
        "canon_markdown": canon,
        "deliverables": [
            {
                "doc_key": "image_prompts" if stage_id == "production" else "shot_prompts" if stage_id == "storyboard" else "shot_video_prompts",
                "format": "items",
                "items": items,
            }
        ]
        if stage_id != "script"
        else [],
    }
    if stage_id == "script":
        payload["deliverables"] = []
    return f"```ryan-stage-export\n{json.dumps(payload, ensure_ascii=False)}\n```"


class TestStageExportAndService(unittest.TestCase):
    def test_parse_and_ready_for_production_items(self):
        text = _export_text(
            "production",
            [{"id": "CHAR_hero", "label": "男主", "text": "pure prompt A"}],
        )
        payload = parse_stage_export(text)
        self.assertEqual(payload.stage_id, "production")
        ready = check_ready(text, load_pipeline().stage("production"))
        self.assertTrue(ready.ready)

    def test_script_ready_without_deliverables(self):
        text = _export_text("script", [])
        ready = check_ready(text, load_pipeline().stage("script"))
        self.assertTrue(ready.ready)

    def test_write_overwrite_and_history(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = CreativeProjectRepository(Path(tmp) / "ryan_creative_workspace")
            project = repo.create_project("demo")
            pid = project["project_id"]
            text1 = _export_text(
                "production",
                [
                    {"id": "CHAR_a", "label": "A", "text": "prompt a"},
                    {"id": "CHAR_b", "label": "B", "text": "prompt b"},
                ],
            )
            payload1 = parse_stage_export(text1)
            write_stage_export(repo, pid, "production", payload1, revision=1)
            items_path = repo.paths(pid).stage_deliverables_dir("production") / "image_prompts.items.md"
            self.assertTrue(items_path.is_file())
            self.assertIn("CHAR_b", items_path.read_text(encoding="utf-8"))

            text2 = _export_text(
                "production",
                [{"id": "CHAR_a", "label": "A", "text": "prompt a2"}],
            )
            write_stage_export(repo, pid, "production", parse_stage_export(text2), revision=2)
            body = items_path.read_text(encoding="utf-8")
            self.assertIn("prompt a2", body)
            self.assertNotIn("CHAR_b", body)
            history = list((repo.paths(pid).stage_deliverables_dir("production") / "history").glob("*.items.md"))
            self.assertTrue(history)

    def test_confirm_draft_and_stale_downstream(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = CreativeProjectRepository(Path(tmp) / "ryan_creative_workspace")
            project = repo.create_project("demo")
            pid = project["project_id"]
            service = CreativeStageService(repo, commit_runner=None)

            # production confirm
            thread = repo.ensure_main_thread(pid, "production")
            export = _export_text(
                "production",
                [{"id": "CHAR_hero", "label": "男主", "text": "hero prompt"}],
            )
            repo.append_thread_record(
                pid,
                "production",
                thread,
                {"role": "assistant", "content": export, "status": "complete"},
            )
            # mark storyboard touched so STALE applies
            state = repo.read_state(pid)
            state["stages"]["storyboard"]["status"] = "LOCKED"
            state["stages"]["storyboard"]["revision"] = 1
            repo.write_state(pid, state)

            result = service.confirm(pid, "production", thread_id=thread, mode="draft")
            self.assertEqual(result["stage"]["status"], "LOCKED")
            storyboard = service.get_stage(pid, "storyboard")
            self.assertEqual(storyboard["status"], "STALE")
            # files remain
            self.assertTrue(
                (repo.paths(pid).stage_deliverables_dir("production") / "image_prompts.items.md").is_file()
            )

            # draft mode without ready fails
            with self.assertRaises(Exception):
                service.confirm(pid, "storyboard", mode="draft")

    def test_selector_items_require_item_and_plain_text(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = CreativeProjectRepository(Path(tmp) / "ryan_creative_workspace")
            project = repo.create_project("demo")
            pid = project["project_id"]
            text = _export_text(
                "storyboard",
                [
                    {"id": "SHOT_001", "label": "开场", "text": "shot one pure"},
                    {"id": "SHOT_002", "label": "转场", "text": "shot two pure"},
                ],
            )
            write_stage_export(repo, pid, "storyboard", parse_stage_export(text), revision=1)
            paths = repo.paths(pid)
            docs = list_project_documents(paths)
            item_doc = next(d for d in docs if d["path"].endswith("shot_prompts.items.md"))
            with self.assertRaises(StageExportError):
                select_document_or_item(paths, item_doc["path"], "")
            selected = select_document_or_item(paths, item_doc["path"], "SHOT_002")
            self.assertEqual(selected["text"], "shot two pure")
            self.assertNotIn("```", selected["text"])
            items = parse_items_markdown(
                (paths.stage_deliverables_dir("storyboard") / "shot_prompts.items.md").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual([i.item_id for i in items], ["SHOT_001", "SHOT_002"])


if __name__ == "__main__":
    unittest.main()
