import tempfile
import unittest
from pathlib import Path

from ryan_comfy_utils.acp.context_builder import build_context_payload
from ryan_comfy_utils.acp.skill_loader import resolve_skill_directory
from ryan_comfy_utils.acp.template_engine import render_context_template


class TestContextBuilder(unittest.TestCase):
    def test_resolve_skill_directory_returns_existing_path(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            skill_root = Path(tmpdir)
            expected = skill_root / "video_prompt_generator"
            expected.mkdir()
            resolved = resolve_skill_directory(skill_root, "video_prompt_generator")
            self.assertEqual(resolved, expected)

    def test_resolve_skill_directory_raises_for_missing_skill(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            skill_root = Path(tmpdir)
            with self.assertRaises(FileNotFoundError):
                resolve_skill_directory(skill_root, "missing_skill")

    def test_build_context_payload_collects_text_and_skill_directory(self):
        payload = build_context_payload(
            skill_id="video_prompt_generator",
            skill_directory=Path("/tmp/skills/video_prompt_generator"),
            user_text="describe this clip",
            image_paths=["input/frame_001.png"],
            file_paths=[],
            workspace_info={"session_dir": "/tmp/session_001"},
        )
        self.assertEqual(payload["skill"]["id"], "video_prompt_generator")
        self.assertEqual(payload["input"]["text"], "describe this clip")
        self.assertEqual(payload["input"]["images"][0], "input/frame_001.png")
        self.assertEqual(payload["workspace"]["session_dir"], "/tmp/session_001")

    def test_render_context_template_replaces_known_placeholders(self):
        template = "读取 Skill:\\n{skill_directory}\\n用户输入:\\n{input.text}"
        payload = {
            "skill": {"directory": "/tmp/skills/video_prompt_generator"},
            "input": {"text": "describe this clip", "images": [], "files": []},
            "workspace": {"session_dir": "/tmp/session_001"},
        }
        rendered = render_context_template(template, payload)
        self.assertIn("/tmp/skills/video_prompt_generator", rendered)
        self.assertIn("describe this clip", rendered)
