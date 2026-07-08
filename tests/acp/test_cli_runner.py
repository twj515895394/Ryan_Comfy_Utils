import tempfile
import unittest
from pathlib import Path

from ryan_comfy_utils.acp.cli_runner import run_cli_command


class TestCLIRunner(unittest.TestCase):
    def test_run_cli_command_captures_stdout_and_stderr(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            result = run_cli_command(
                command=[
                    "python3",
                    "-c",
                    "import sys; print('hello from cli'); print('warn', file=sys.stderr)",
                ],
                cwd=Path(tmpdir),
                timeout_seconds=10,
                env_overrides={},
            )
            self.assertEqual(result["returncode"], 0)
            self.assertIn("hello from cli", result["stdout"])
            self.assertIn("warn", result["stderr"])
