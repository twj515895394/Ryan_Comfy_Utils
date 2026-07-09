import tempfile
import unittest
from pathlib import Path

from ryan_comfy_utils.acp.runtime import execute_text_session, map_result_fields


def _skill_root_with(skill_id: str, root: Path) -> Path:
    skill_root = root / "skills"
    (skill_root / skill_id).mkdir(parents=True)
    return skill_root


class TestACPRuntime(unittest.TestCase):
    def test_execute_text_session_returns_response_and_session_paths(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            skill_root = _skill_root_with("video_prompt_generator", root)
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
            prompt = Path(result["session_dir"]) / "input" / "prompt.txt"
            self.assertTrue(prompt.exists())
            self.assertIn("describe this clip", prompt.read_text(encoding="utf-8"))

    def test_execute_text_session_injects_asset_paths_into_context(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            skill_root = _skill_root_with("video_prompt_generator", root)
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
            self.assertIn("input/images/", context_text)
            self.assertIn("frame_001.png", context_text)
            self.assertIn("input/files/", context_text)
            self.assertIn("notes.txt", context_text)

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

    def test_map_result_fields_missing_path_returns_empty_string(self):
        mapped = map_result_fields({"outputs": {}}, {"response_text": "outputs.missing"})
        self.assertEqual(mapped["response_text"], "")

    def test_context_file_placeholder_is_readable_by_cli(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            skill_root = _skill_root_with("video_prompt_generator", root)
            command = [
                "python3",
                "-c",
                (
                    "import pathlib, sys; "
                    "p = pathlib.Path(sys.argv[1]); "
                    "print(p.read_text(encoding='utf-8'))"
                ),
                "{context_file}",
            ]
            result = execute_text_session(
                workspace_root=root,
                session_id="session_ctx",
                skill_root=skill_root,
                skill_id="video_prompt_generator",
                context_template="MARKER:{input.text}",
                user_text="inject-me",
                runner_profile={
                    "runner": "test_runner",
                    "command": command,
                    "timeout_seconds": 10,
                    "environment": {},
                },
            )
            self.assertIn("MARKER:inject-me", result["outputs"]["response_text"])

    def test_nonzero_returncode_raises(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            skill_root = _skill_root_with("video_prompt_generator", root)
            with self.assertRaises(RuntimeError) as ctx:
                execute_text_session(
                    workspace_root=root,
                    session_id="session_fail",
                    skill_root=skill_root,
                    skill_id="video_prompt_generator",
                    context_template="{input.text}",
                    user_text="x",
                    runner_profile={
                        "runner": "test_runner",
                        "command": ["python3", "-c", "import sys; sys.exit(2)"],
                        "timeout_seconds": 10,
                        "environment": {},
                    },
                )
            self.assertIn("returncode=2", str(ctx.exception))

    def test_result_json_error_status_raises(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            skill_root = _skill_root_with("video_prompt_generator", root)
            command = [
                "python3",
                "-c",
                (
                    "import json, pathlib; "
                    "pathlib.Path('output/result.json').write_text("
                    "json.dumps({'status': 'error', 'outputs': {}, 'message': 'boom'}), "
                    "encoding='utf-8')"
                ),
            ]
            with self.assertRaises(RuntimeError) as ctx:
                execute_text_session(
                    workspace_root=root,
                    session_id="session_err_status",
                    skill_root=skill_root,
                    skill_id="video_prompt_generator",
                    context_template="{input.text}",
                    user_text="x",
                    runner_profile={
                        "runner": "test_runner",
                        "command": command,
                        "timeout_seconds": 10,
                        "environment": {},
                    },
                )
            self.assertIn("status=error", str(ctx.exception))

    def test_invalid_result_json_raises(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            skill_root = _skill_root_with("video_prompt_generator", root)
            command = [
                "python3",
                "-c",
                (
                    "import pathlib; "
                    "pathlib.Path('output/result.json').write_text('not-json', encoding='utf-8')"
                ),
            ]
            with self.assertRaises(RuntimeError) as ctx:
                execute_text_session(
                    workspace_root=root,
                    session_id="session_bad_json",
                    skill_root=skill_root,
                    skill_id="video_prompt_generator",
                    context_template="{input.text}",
                    user_text="x",
                    runner_profile={
                        "runner": "test_runner",
                        "command": command,
                        "timeout_seconds": 10,
                        "environment": {},
                    },
                )
            self.assertIn("Invalid result.json", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
