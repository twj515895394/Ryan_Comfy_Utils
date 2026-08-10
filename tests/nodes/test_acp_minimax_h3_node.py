import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from ryan_comfy_utils.acp.contracts import load_manifest
from ryan_comfy_utils.nodes.acp_nodes import (
    DEFAULT_MINIMAX_H3_VIDEO_PROMPT_MANIFEST_PATH,
    H3_GENERATION_MODES,
    RyanACPMiniMaxH3VideoPromptAgent,
)


class TestACPMinimaxH3Node(unittest.TestCase):
    def test_manifest_accepts_images_and_files(self):
        manifest = load_manifest(DEFAULT_MINIMAX_H3_VIDEO_PROMPT_MANIFEST_PATH)
        self.assertTrue(manifest["input_contract"]["text"])
        self.assertTrue(manifest["input_contract"]["images"])
        self.assertTrue(manifest["input_contract"]["files"])
        self.assertIn("h3-style-routing.md", manifest["context_template"])
        self.assertIn("{input.files}", manifest["context_template"])

    def test_input_types_preserve_legacy_order_and_modes(self):
        node = RyanACPMiniMaxH3VideoPromptAgent()
        input_types = node.INPUT_TYPES()
        self.assertEqual(input_types["required"]["generation_mode"][1]["default"], "纯文生")
        self.assertEqual(
            list(input_types["optional"].keys())[-3:],
            ["task_relation", "image_role_mapping", "asset_role_mapping"],
        )
        self.assertIn("首帧生成", H3_GENERATION_MODES)
        self.assertIn("尾帧生成", H3_GENERATION_MODES)
        self.assertIn("全能参考", H3_GENERATION_MODES)
        self.assertEqual(input_types["optional"]["image_slot_count"][1]["min"], 0)

    @patch("ryan_comfy_utils.nodes.acp_nodes.run_fixed_acp_agent")
    def test_run_without_video_ignores_frame_controls(self, run_fixed):
        run_fixed.return_value = ("H3 video prompt result", "/tmp/s_h3", "{}")
        node = RyanACPMiniMaxH3VideoPromptAgent()
        out = node.run(
            generation_mode="纯文生",
            user_text="a futuristic city at night",
            export_to_file=False,
            image_slot_count=0,
            video_slot_count=0,
            video_start_frame=999,
            video_frame_count=20,
            audio_slot_count=0,
        )
        self.assertEqual(out[0], "H3 video prompt result")
        kwargs = run_fixed.call_args.kwargs
        self.assertEqual(kwargs["image_slots"], [])
        self.assertEqual(kwargs["file_paths"], "")
        self.assertIn("基础生成模式: T2VA", kwargs["extra_user_lines"])
        self.assertIn("素材清单:\n- 无（纯文本生成场景）", kwargs["extra_user_lines"])

    @patch("ryan_comfy_utils.nodes.acp_nodes.run_fixed_acp_agent")
    def test_run_passes_video_audio_files_and_role_mapping(self, run_fixed):
        run_fixed.return_value = ("prompt", "/tmp/s_h3", "{}")
        node = RyanACPMiniMaxH3VideoPromptAgent()
        with tempfile.TemporaryDirectory() as tmpdir:
            video_path = Path(tmpdir) / "source.mp4"
            audio_path = Path(tmpdir) / "voice.wav"
            video_path.touch()
            audio_path.touch()
            node.run(
                generation_mode="全能参考",
                task_relation="Audio Reference（音频参考）",
                image_role_mapping="图片1=人物参考",
                asset_role_mapping="视频1=动作参考\n音频1=音色参考",
                user_text="Create a new scene.",
                export_to_file=False,
                image_slot_count=0,
                video_slot_count=1,
                audio_slot_count=1,
                video_01=str(video_path),
                audio_01=str(audio_path),
            )

        kwargs = run_fixed.call_args.kwargs
        self.assertIn(str(video_path), kwargs["file_paths"])
        self.assertIn(str(audio_path), kwargs["file_paths"])
        self.assertIn("基础生成模式: Ref2VA", kwargs["extra_user_lines"])
        self.assertIn("附加任务关系: Audio Reference（音频参考）", kwargs["extra_user_lines"])
        self.assertIn("图片角色映射:", kwargs["extra_user_lines"])
        self.assertIn("素材角色映射:", kwargs["extra_user_lines"])


if __name__ == "__main__":
    unittest.main()
