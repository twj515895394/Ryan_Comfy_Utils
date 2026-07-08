import json
import unittest
from pathlib import Path

from ryan_comfy_utils.acp.contracts import (
    load_manifest,
    load_profile,
    validate_result_payload,
)


class TestACPContracts(unittest.TestCase):
    def test_load_manifest_reads_required_fields(self):
        manifest = load_manifest(
            Path("ryan_comfy_utils/acp/fixtures/manifests/universal_agent.json")
        )
        self.assertEqual(manifest["node_id"], "ryan.acp.universal_agent")
        self.assertEqual(manifest["mode"], "selectable")
        self.assertEqual(manifest["output_contract"]["type"], "text")

    def test_load_profile_reads_command_and_timeout(self):
        profile = load_profile(
            Path("ryan_comfy_utils/acp/fixtures/profiles/local_codex.json")
        )
        self.assertEqual(profile["runner"], "codex_cli")
        self.assertGreater(profile["timeout_seconds"], 0)

    def test_validate_result_payload_requires_status_and_outputs(self):
        payload = json.loads(
            Path("ryan_comfy_utils/acp/fixtures/results/text_success.json").read_text(
                encoding="utf-8"
            )
        )
        validated = validate_result_payload(payload)
        self.assertEqual(validated["status"], "ok")
        self.assertIn("response_text", validated["outputs"])
