import tempfile
import unittest
from pathlib import Path

from ryan_comfy_utils.acp.runtime import execute_text_session, map_result_fields


class TestACPRuntime(unittest.TestCase):
    def test_execute_text_session_returns_response_and_session_paths(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            skill_root = root / "skills"
            (skill_root / "video_prompt_generator").mkdir(parents=True)
            result = execute_text_session(
                workspace_root=root,
                session_id="session_001",
                skill_root=skill_root,
                skill_id="video_prompt_generator",
                context_template="用户输入:\\n{input.text}",
                user_text="describe this clip",
                runner_profile={
                    "runner": "test_runner",
                    "command": ["python3", "-c", "print('hello from runtime')"],
                    "timeout_seconds": 10,
                    "environment": {},
                },
            )
            self.assertEqual(result["outputs"]["response_text"], "hello from runtime")
            self.assertTrue(result["session_dir"].endswith("session_001"))
            self.assertEqual(result["raw_result_json"]["returncode"], 0)

    def test_execute_text_session_injects_asset_paths_into_context(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            skill_root = root / "skills"
            (skill_root / "video_prompt_generator").mkdir(parents=True)
            image_source = root / "frame_001.png"
            image_source.write_bytes(b"fake-image-data")
            file_source = root / "notes.txt"
            file_source.write_text("hello file", encoding="utf-8")
            command = [
                "python3",
                "-c",
                (
                    "import json, pathlib; "
                    "path = pathlib.Path('output/result.json'); "
                    "path.write_text(json.dumps({'status': 'ok', 'outputs': {'response_text': 'done'}}), encoding='utf-8')"
                ),
            ]
            result = execute_text_session(
                workspace_root=root,
                session_id="session_002",
                skill_root=skill_root,
                skill_id="video_prompt_generator",
                context_template="图片:\\n{input.images}\\n文件:\\n{input.files}",
                user_text="describe this clip",
                runner_profile={
                    "runner": "test_runner",
                    "command": command,
                    "timeout_seconds": 10,
                    "environment": {},
                },
                image_inputs=[str(image_source)],
                file_inputs=[str(file_source)],
            )
            context_path = Path(result["session_dir"]) / "context.json"
            context_text = context_path.read_text(encoding="utf-8")
            self.assertIn("input/images/frame_001.png", context_text)
            self.assertIn("input/files/notes.txt", context_text)

    def test_map_result_fields_reads_manifest_mapping_paths(self):
        payload = {
            "outputs": {"answer_text": "hello from mapping"},
            "raw_result_json": {"returncode": 0},
        }
        mapped = map_result_fields(
            payload,
            {
                "response_text": "outputs.answer_text",
                "raw_result_json": "raw_result_json",
            },
        )
        self.assertEqual(mapped["response_text"], "hello from mapping")
        self.assertEqual(mapped["raw_result_json"]["returncode"], 0)
