import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch

from ryan_comfy_utils.acp.pi_runner import (
    RYAN_SYSTEM_PROMPT,
    build_pi_command,
    probe_pi_cli,
)


class TestPiRunner(unittest.TestCase):
    def test_build_pi_command_injects_safe_runtime_options(self):
        command = build_pi_command(
            {
                "runner": "pi_cli",
                "command": ["pi", "-p", "{context}"],
                "mode": "text",
                "no_context_files": True,
                "use_skill_flag": True,
                "tool_policy": "full",
            },
            Path("output/acp_workspace/workflows/wf/agents/agent"),
        )

        self.assertNotIn("{context}", command)
        self.assertIn("--mode", command)
        self.assertEqual(command[command.index("--mode") + 1], "text")
        self.assertIn("--no-context-files", command)
        self.assertIn("--skill", command)
        self.assertIn("{skill_directory}", command)
        self.assertIn("--system-prompt", command)
        self.assertIn(RYAN_SYSTEM_PROMPT, command)
        self.assertIn("--tools", command)
        self.assertNotIn("--api-key", command)

    def test_build_pi_command_rejects_non_text_mode(self):
        with self.assertRaisesRegex(ValueError, "mode=text"):
            build_pi_command(
                {"runner": "pi_cli", "command": ["pi"], "mode": "rpc"},
                Path("skill"),
            )

    @patch("ryan_comfy_utils.acp.pi_runner.shutil.which", return_value="pi")
    @patch("ryan_comfy_utils.acp.pi_runner.subprocess.run")
    def test_probe_checks_pi_help_capabilities(self, run, _which):
        run.return_value = subprocess.CompletedProcess(
            ["pi", "--help"],
            0,
            stdout="--mode --no-context-files --skill",
            stderr="",
        )

        probe_pi_cli(["pi", "-p"])

        run.assert_called_once()
        self.assertEqual(run.call_args.args[0], ["pi", "--help"])

    @patch("ryan_comfy_utils.acp.pi_runner.shutil.which", return_value="pi")
    @patch("ryan_comfy_utils.acp.pi_runner.subprocess.run")
    def test_probe_rejects_missing_required_option(self, run, _which):
        run.return_value = subprocess.CompletedProcess(
            ["pi", "--help"], 0, stdout="--mode", stderr=""
        )

        with self.assertRaisesRegex(RuntimeError, "--no-context-files"):
            probe_pi_cli(["pi", "-p"])


    @patch("ryan_comfy_utils.acp.runtime.probe_pi_cli")
    @patch("ryan_comfy_utils.acp.runtime.run_cli_command")
    def test_execute_text_session_uses_pi_branch_and_preserves_result_contract(
        self, run_cli, probe
    ):
        from tempfile import TemporaryDirectory

        from ryan_comfy_utils.acp.runtime import execute_text_session

        def fake_run_cli(**kwargs):
            output_path = Path(kwargs["cwd"]) / "output" / "result.json"
            output_path.write_text(
                '{"status": "ok", "outputs": {"response_text": "pi result"}}',
                encoding="utf-8",
            )
            return {"returncode": 0, "stdout": "", "stderr": ""}

        run_cli.side_effect = fake_run_cli

        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            skill_root = root / "skills"
            (skill_root / "demo").mkdir(parents=True)
            result = execute_text_session(
                workspace_root=root,
                session_id="pi_session",
                skill_root=skill_root,
                skill_id="demo",
                context_template="{input.text}",
                user_text="hello",
                runner_profile={
                    "runner": "pi_cli",
                    "command": ["pi", "-p"],
                    "mode": "text",
                    "no_context_files": True,
                    "use_skill_flag": True,
                    "tool_policy": "full",
                    "timeout_seconds": 10,
                    "environment": {},
                },
            )

        probe.assert_called_once()
        command = run_cli.call_args.kwargs["command"]
        self.assertIn("--mode", command)
        self.assertIn("--skill", command)
        self.assertEqual(result["outputs"]["response_text"], "pi result")

if __name__ == "__main__":
    unittest.main()

