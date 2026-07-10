import sys
import types
import unittest
from unittest.mock import patch, MagicMock

# Provide stubs for ComfyUI modules if not present
for mod_name in ("folder_paths", "server", "aiohttp", "aiohttp.web"):
    if mod_name not in sys.modules:
        sys.modules[mod_name] = types.ModuleType(mod_name)

sys.modules["folder_paths"].get_output_directory = lambda: "/tmp/comfyui_output"
sys.modules["folder_paths"].get_temp_directory = lambda: "/tmp/comfyui_temp"

from ryan_comfy_utils.nodes.video_nodes import RyanVideoFrameSampler, SAMPLE_MODE_MAP


class TestRyanVideoFrameSampler(unittest.TestCase):
    def test_input_types(self):
        inputs = RyanVideoFrameSampler.INPUT_TYPES()
        self.assertIn("sample_mode", inputs["required"])
        # Optional inputs
        self.assertIn("video_path", inputs["optional"])
        self.assertIn("scene_detector", inputs["optional"])
        self.assertIn("scene_threshold", inputs["optional"])
        self.assertIn("scene_min_len", inputs["optional"])
        self.assertIn("scene_merge_min", inputs["optional"])

    def test_sample_mode_contains_scene(self):
        self.assertIn("分镜首帧采样", SAMPLE_MODE_MAP)
        self.assertEqual(SAMPLE_MODE_MAP["分镜首帧采样"], "scene_first_frame")

    @patch("ryan_comfy_utils.nodes.video_nodes.Path.exists")
    @patch("ryan_comfy_utils.nodes.video_nodes.detect_scenes")
    @patch("ryan_comfy_utils.nodes.video_nodes.merge_short_scenes")
    @patch("ryan_comfy_utils.nodes.video_nodes.get_scene_first_frames")
    @patch("ryan_comfy_utils.nodes.video_nodes.get_video_info")
    def test_sample_scene_first_frame(self, mock_get_video_info, mock_first_frames, mock_merge, mock_detect, mock_exists):
        # Configure mocks
        mock_exists.return_value = True
        mock_detect.return_value = ["scene_1", "scene_2"]
        mock_merge.return_value = [("start1", "end1"), ("start2", "end2")]
        
        import torch
        mock_tensor = torch.zeros((2, 64, 64, 3))
        mock_first_frames.return_value = mock_tensor
        mock_get_video_info.return_value = {"fps": 30.0}

        sampler = RyanVideoFrameSampler()
        
        # Mock timecode seconds
        mock_time1 = MagicMock()
        mock_time1.get_seconds.return_value = 1.0
        mock_time2 = MagicMock()
        mock_time2.get_seconds.return_value = 2.5
        
        mock_merge.return_value = [
            (mock_time1, MagicMock()),
            (mock_time2, MagicMock())
        ]

        result = sampler.sample(
            sample_mode="分镜首帧采样",
            frame_count=2,
            frame_interval=1,
            custom_indexes="0,-1",
            save_mode="仅预览不保存",
            output_subdir="test",
            filename_prefix="test",
            images=None,
            video_path="/path/to/video.mp4",
            scene_detector="自适应检测",
            scene_threshold=0.0,
            scene_min_len=0.6,
            scene_merge_min=1.0
        )
        
        # Check returned tuple: (sampled, frame_indexes_str, count, saved_paths)
        self.assertIs(result[0], mock_tensor)
        self.assertEqual(result[1], "30,75") # 1.0s * 30fps = 30; 2.5s * 30fps = 75
        self.assertEqual(result[2], 2)
        self.assertEqual(result[3], "")

    @patch("ryan_comfy_utils.nodes.video_nodes._LAST_LOADED_VIDEO_PATH", None)
    def test_sample_scene_first_frame_no_path(self):
        sampler = RyanVideoFrameSampler()
        import ryan_comfy_utils.nodes.video_nodes as vn
        vn._LAST_LOADED_VIDEO_PATH = None
        with self.assertRaises(FileNotFoundError):
            sampler.sample(
                sample_mode="分镜首帧采样",
                frame_count=2,
                frame_interval=1,
                custom_indexes="0,-1",
                save_mode="仅预览不保存",
                output_subdir="test",
                filename_prefix="test",
                images=None,
                video_path=""
            )

    @patch("ryan_comfy_utils.nodes.video_nodes.Path.exists")
    @patch("ryan_comfy_utils.nodes.video_nodes.detect_scenes")
    @patch("ryan_comfy_utils.nodes.video_nodes.merge_short_scenes")
    @patch("ryan_comfy_utils.nodes.video_nodes.get_scene_first_frames")
    @patch("ryan_comfy_utils.nodes.video_nodes.get_video_info")
    def test_sample_scene_first_frame_fallback(self, mock_get_video_info, mock_first_frames, mock_merge, mock_detect, mock_exists):
        mock_exists.return_value = True
        mock_detect.return_value = ["scene_1"]
        
        import torch
        mock_tensor = torch.zeros((1, 64, 64, 3))
        mock_first_frames.return_value = mock_tensor
        mock_get_video_info.return_value = {"fps": 30.0}

        mock_time1 = MagicMock()
        mock_time1.get_seconds.return_value = 1.0
        mock_merge.return_value = [(mock_time1, MagicMock())]

        import ryan_comfy_utils.nodes.video_nodes as vn
        vn._LAST_LOADED_VIDEO_PATH = "/cached/video.mp4"

        sampler = RyanVideoFrameSampler()
        result = sampler.sample(
            sample_mode="分镜首帧采样",
            frame_count=2,
            frame_interval=1,
            custom_indexes="0,-1",
            save_mode="仅预览不保存",
            output_subdir="test",
            filename_prefix="test",
            images=None,
            video_path="",  # empty to trigger fallback
            scene_detector="自适应检测",
            scene_threshold=0.0,
            scene_min_len=0.6,
            scene_merge_min=1.0
        )
        self.assertIs(result[0], mock_tensor)
        self.assertEqual(result[1], "30")
        self.assertEqual(result[2], 1)


if __name__ == "__main__":
    unittest.main()
