import tempfile
import unittest
from pathlib import Path

from ryan_comfy_utils.acp.runtime import execute_text_session


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
