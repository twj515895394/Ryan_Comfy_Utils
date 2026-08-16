import tempfile
import unittest
from pathlib import Path

from ryan_comfy_utils.creative_workspace.asset_bridge import ComfyTVAssetBridge
from ryan_comfy_utils.creative_workspace.chat_service import CreativeChatService
from ryan_comfy_utils.creative_workspace.project_repository import CreativeProjectRepository
from ryan_comfy_utils.nodes.creative_text_selector_node import RyanCreativeTextSelector


class FakeRunner:
    def __init__(self, text: str):
        self.text = text
        self.stopped = False

    def run(self, **kwargs):
        yield {"type": "delta", "text": self.text[:10]}
        yield {"type": "delta", "text": self.text[10:]}
        yield {"type": "end"}

    def stop(self):
        self.stopped = True


class TestChatAndBridge(unittest.TestCase):
    def test_discuss_uses_current_thread_and_fake_runner(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = CreativeProjectRepository(Path(tmp) / "ryan_creative_workspace")
            project = repo.create_project("chat")
            pid = project["project_id"]
            export = (
                "```ryan-stage-export\n"
                '{"stage_id":"creative","canon_markdown":"# Story\\n","deliverables":[]}\n'
                "```"
            )
            published = []
            chat = CreativeChatService(
                repo,
                rpc_runner=FakeRunner(export),
                event_publisher=published.append,
            )
            result = chat.discuss(
                project_id=pid,
                stage_id="creative",
                message="写一个雨夜故事",
            )
            self.assertEqual(result["status"], "complete")
            self.assertIn("ryan-stage-export", result["text"])
            self.assertTrue(result["ready"]["ready"])
            types = [e.get("type") for e in published]
            self.assertIn("start", types)
            self.assertIn("delta", types)
            self.assertIn("end", types)
            records = repo.read_thread_records(pid, "creative", result["thread_id"])
            roles = [r["role"] for r in records]
            self.assertEqual(roles[-2:], ["user", "assistant"])

            # messages API shape via repository records
            self.assertGreaterEqual(len(records), 2)
    def test_asset_bridge_unavailable_lists_empty_and_local_ref(self):
        bridge = ComfyTVAssetBridge(
            http_json=lambda *a, **k: (_ for _ in ()).throw(ConnectionError("down"))
        )
        self.assertFalse(bridge.available())
        self.assertEqual(bridge.list_assets(), [])
        ref = bridge.make_local_ref(__file__, media_type="image", display_name="x")
        compiled = bridge.compile_refs([ref])
        self.assertIn("ASSET image", compiled.text)
        self.assertTrue(compiled.attachment_paths)

    def test_save_local_upload_creates_file_ref(self):
        with tempfile.TemporaryDirectory() as tmp:
            bridge = ComfyTVAssetBridge(
                http_json=lambda *a, **k: (_ for _ in ()).throw(ConnectionError("down"))
            )
            ref = bridge.save_local_upload(
                project_uploads_dir=Path(tmp) / "uploads",
                filename="shot.png",
                data=b"fake-image-bytes",
                media_type="image",
            )
            self.assertEqual(ref["provider"], "local")
            self.assertEqual(ref["media_type"], "image")
            self.assertTrue(Path(ref["local_path"]).is_file())

    def test_artifact_selector_module_removed_and_text_selector_exists(self):
        root = Path(__file__).resolve().parents[2]
        self.assertFalse((root / "ryan_comfy_utils/nodes/artifact_selector_node.py").is_file())
        self.assertFalse(
            (root / "ryan_comfy_utils/web/workflow_agent/artifact_selector_extension.js").is_file()
        )
        self.assertTrue((root / "ryan_comfy_utils/nodes/creative_text_selector_node.py").is_file())
        self.assertEqual(RyanCreativeTextSelector.RETURN_TYPES, ("STRING",))
        # package root __init__ source no longer registers Artifact Selector
        init_text = (root / "__init__.py").read_text(encoding="utf-8")
        self.assertNotIn("Ryan Artifact Selector", init_text)
        self.assertIn("Ryan Creative Text Selector", init_text)
        self.assertNotIn("artifact_selector", init_text)


if __name__ == "__main__":
    unittest.main()
