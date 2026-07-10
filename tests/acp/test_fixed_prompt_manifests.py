import unittest
from pathlib import Path

from ryan_comfy_utils.acp.contracts import load_manifest
from ryan_comfy_utils.acp.skill_loader import resolve_skill_directory, resolve_skill_root
from ryan_comfy_utils.nodes.acp_nodes import (
    DEFAULT_IMAGE_PROMPT_MANIFEST_PATH,
    DEFAULT_VIDEO_PROMPT_MANIFEST_PATH,
    PACKAGE_ROOT,
    parse_multiline_paths,
    run_fixed_acp_agent,
)


class TestFixedPromptManifests(unittest.TestCase):
    def test_image_prompt_manifest_is_fixed_mode(self):
        manifest = load_manifest(DEFAULT_IMAGE_PROMPT_MANIFEST_PATH)
        self.assertEqual(manifest["node_id"], "ryan.acp.image_prompt_agent")
        self.assertEqual(manifest["mode"], "fixed")
        self.assertEqual(manifest["skill_id"], "image-prompt-skill")
        self.assertTrue(manifest["input_contract"]["text"])
        self.assertTrue(manifest["input_contract"]["images"])

    def test_video_prompt_manifest_is_fixed_mode(self):
        manifest = load_manifest(DEFAULT_VIDEO_PROMPT_MANIFEST_PATH)
        self.assertEqual(manifest["node_id"], "ryan.acp.video_prompt_agent")
        self.assertEqual(manifest["mode"], "fixed")
        self.assertEqual(manifest["skill_id"], "video-prompt-skill")

    def test_resolve_skill_root_falls_back_to_package_fixtures(self):
        root = resolve_skill_root("")
        self.assertEqual(root, PACKAGE_ROOT / "acp" / "fixtures" / "skills")
        self.assertTrue((root / "image-prompt-skill").is_dir())
        self.assertTrue((root / "video-prompt-skill").is_dir())

    def test_resolve_skill_directory_under_default_root(self):
        skill_root = resolve_skill_root("")
        path = resolve_skill_directory(skill_root, "image-prompt-skill")
        self.assertTrue((path / "SKILL.md").is_file())

    def test_parse_multiline_paths_strips_empty_lines(self):
        self.assertEqual(
            parse_multiline_paths("a.png\n\nb.png\n"),
            ["a.png", "b.png"],
        )

    def test_run_fixed_acp_agent_passes_skill_and_assets(self):
        from unittest.mock import patch

        with patch("ryan_comfy_utils.nodes.acp_nodes.execute_text_session") as execute:
            execute.return_value = {
                "outputs": {"response_text": "prompt out"},
                "session_dir": "/tmp/s1",
                "raw_result_json": {"returncode": 0},
            }
            response_text, session_dir, _raw = run_fixed_acp_agent(
                manifest_path=str(DEFAULT_IMAGE_PROMPT_MANIFEST_PATH),
                profile_path=str(PACKAGE_ROOT / "acp" / "fixtures" / "profiles" / "local_codex.json"),
                workspace_root="/tmp/ws",
                session_id="s1",
                skill_root="",
                user_text="a cat in rain",
                image_paths="ref.png",
                file_paths="",
            )
            self.assertEqual(response_text, "prompt out")
            self.assertEqual(session_dir, "/tmp/s1")
            call_kw = execute.call_args.kwargs
            self.assertEqual(call_kw["skill_id"], "image-prompt-skill")
            self.assertEqual(call_kw["image_inputs"], ["ref.png"])


if __name__ == "__main__":
    unittest.main()