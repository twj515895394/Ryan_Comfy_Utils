import sys
import types
import unittest
from unittest.mock import MagicMock

# Provide lightweight stubs for ComfyUI-only modules so we can import
# video_nodes in a plain test environment.
for mod_name in ("folder_paths", "server", "aiohttp", "aiohttp.web"):
    if mod_name not in sys.modules:
        sys.modules[mod_name] = types.ModuleType(mod_name)

sys.modules["folder_paths"].get_output_directory = lambda: "/tmp/comfyui_output"
sys.modules["folder_paths"].get_temp_directory = lambda: "/tmp/comfyui_temp"

_mock_server = sys.modules["server"]
_prompt_server = MagicMock()
_mock_server.PromptServer = MagicMock()
_mock_server.PromptServer.instance = _prompt_server

_mock_web = sys.modules["aiohttp.web"]
_mock_web.json_response = MagicMock()
_mock_web.Response = MagicMock()
_mock_web.FileResponse = MagicMock()
sys.modules["aiohttp"].web = _mock_web

from ryan_comfy_utils.nodes.video_nodes import RyanVideoSceneSplitter, DETECTOR_MAP


class TestRyanVideoSceneSplitterContract(unittest.TestCase):
    """验证 RyanVideoSceneSplitter 节点的 ComfyUI 合约。"""

    def test_input_types_required_keys(self):
        inputs = RyanVideoSceneSplitter.INPUT_TYPES()
        required = inputs["required"]
        expected_keys = {
            "video_path", "output_dir", "filename_prefix",
            "detector", "threshold", "min_scene_len",
            "merge_min_duration", "fast_copy",
            "force_rate", "custom_width", "custom_height",
            "frame_load_cap", "skip_first_frames", "select_every_nth",
        }
        self.assertEqual(set(required.keys()), expected_keys)

    def test_return_types(self):
        self.assertEqual(RyanVideoSceneSplitter.RETURN_TYPES, ("INT", "STRING", "STRING"))

    def test_return_names(self):
        self.assertEqual(RyanVideoSceneSplitter.RETURN_NAMES, ("scene_count", "manifest_json", "output_dir"))

    def test_function_name(self):
        self.assertEqual(RyanVideoSceneSplitter.FUNCTION, "run")

    def test_category(self):
        self.assertEqual(RyanVideoSceneSplitter.CATEGORY, "Ryan Utils / Video")


class TestDetectorMap(unittest.TestCase):
    """验证中文检测器选项映射。"""

    def test_detector_map_values(self):
        self.assertEqual(DETECTOR_MAP["自适应检测"], "adaptive")
        self.assertEqual(DETECTOR_MAP["内容突变检测"], "content")
        self.assertEqual(DETECTOR_MAP["亮度阈值检测"], "threshold")

    def test_detector_map_has_three_entries(self):
        self.assertEqual(len(DETECTOR_MAP), 3)


class TestRyanVideoSceneSplitterRun(unittest.TestCase):
    """验证 RyanVideoSceneSplitter 节点的 run 方法。"""

    from unittest.mock import patch

    @patch("ryan_comfy_utils.nodes.video_nodes.Path.exists")
    @patch("ryan_comfy_utils.nodes.video_nodes.detect_scenes")
    @patch("ryan_comfy_utils.nodes.video_nodes.merge_short_scenes")
    @patch("ryan_comfy_utils.nodes.video_nodes.split_video_to_files")
    def test_run_success(self, mock_split, mock_merge, mock_detect, mock_exists):
        mock_exists.return_value = True
        mock_detect.return_value = ["scene_1"]
        mock_merge.return_value = [("start", "end")]
        mock_split.return_value = [
            {
                "scene_number": 1,
                "start_timecode": "00:00:00.000",
                "end_timecode": "00:00:05.000",
                "start_seconds": 0.0,
                "end_seconds": 5.0,
                "duration_seconds": 5.0,
                "file_path": "/tmp/comfyui_output/scene_splits/scene_001.mp4"
            }
        ]

        node = RyanVideoSceneSplitter()
        count, manifest_json, output_dir = node.run(
            video_path="/path/to/video.mp4",
            output_dir="scene_splits",
            filename_prefix="scene",
            detector="自适应检测",
            threshold=0.0,
            min_scene_len=0.6,
            merge_min_duration=1.0,
            fast_copy=False
        )

        self.assertEqual(count, 1)
        self.assertIn("scene_001.mp4", manifest_json)
        self.assertTrue(output_dir.replace("\\", "/").endswith("scene_splits"))

    def test_run_file_not_found(self):
        node = RyanVideoSceneSplitter()
        with self.assertRaises(FileNotFoundError):
            node.run(
                video_path="/non_existent_file.mp4",
                output_dir="scene_splits",
                filename_prefix="scene",
                detector="自适应检测",
                threshold=0.0,
                min_scene_len=0.6,
                merge_min_duration=1.0,
                fast_copy=False
            )


if __name__ == "__main__":
    unittest.main()
