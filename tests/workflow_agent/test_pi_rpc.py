import sys
import tempfile
import unittest
from pathlib import Path

from ryan_comfy_utils.workflow_agent.pi_rpc import PiRpcError, PiRpcRunner, build_pi_rpc_command


class TestPiRpcRunner(unittest.TestCase):
    def test_run_uses_json_prompt_protocol_and_waits_for_settlement(self):
        script = (
            "import json, sys\n"
            "command = json.loads(sys.stdin.readline())\n"
            "assert command['type'] == 'prompt'\n"
            "assert command['message'] == 'hello'\n"
            "print(json.dumps({'type': 'response', 'command': 'prompt', 'success': True}), flush=True)\n"
            "print(json.dumps({'type': 'message_update', 'assistantMessageEvent': {'type': 'text_delta', 'delta': 'rpc-ok'}}), flush=True)\n"
            "print(json.dumps({'type': 'agent_end', 'messages': [{'role': 'assistant', 'content': [{'type': 'text', 'text': 'rpc-ok'}]}]}), flush=True)\n"
            "print(json.dumps({'type': 'agent_settled'}), flush=True)\n"
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            helper = root / "fake_pi.py"
            helper.write_text(script, encoding="utf-8")
            runner = PiRpcRunner(
                {"command": [sys.executable, str(helper)]},
                probe=False,
            )
            events = list(
                runner.run(
                    skill_directory=root,
                    session_dir=root,
                    prompt="hello",
                    timeout_seconds=5,
                )
            )

            self.assertEqual([event["text"] for event in events if event.get("text")], ["rpc-ok"])
            self.assertEqual(runner.status, "completed")

    def test_run_rejects_zero_exit_without_agent_settlement(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            runner = PiRpcRunner(
                {"command": [sys.executable, "-c", "print('rpc-ok')"]},
                probe=False,
            )

            with self.assertRaisesRegex(PiRpcError, "agent settled"):
                list(
                    runner.run(
                        skill_directory=root,
                        session_dir=root,
                        prompt="hello",
                        timeout_seconds=5,
                    )
                )

            self.assertEqual(runner.status, "error")

    def test_run_reports_nonzero_exit_as_pi_rpc_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            runner = PiRpcRunner(
                {"command": [sys.executable, "-c", "raise SystemExit(3)"]},
                probe=False,
            )

            with self.assertRaises(PiRpcError):
                list(
                    runner.run(
                        skill_directory=root,
                        session_dir=root,
                        prompt="hello",
                        timeout_seconds=5,
                    )
                )

            self.assertEqual(runner.status, "error")
    def test_build_command_isolated_from_global_session_and_ui_prompts(self):
        command = build_pi_rpc_command({}, Path("skill"))
        self.assertIn("--no-session", command)
        self.assertIn("--approve", command)



if __name__ == "__main__":
    unittest.main()
