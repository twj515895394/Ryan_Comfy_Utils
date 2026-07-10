import unittest
from unittest.mock import patch, MagicMock, PropertyMock
from ryan_comfy_utils.core.scene_detect import merge_short_scenes, DEFAULT_THRESHOLDS


class MockTimecode:
    """模拟 PySceneDetect 的 FrameTimecode 对象。"""
    def __init__(self, seconds: float):
        self._seconds = seconds

    def get_seconds(self):
        return self._seconds

    def get_timecode(self):
        m, s = divmod(self._seconds, 60)
        h, m = divmod(int(m), 60)
        return f"{h:02d}:{int(m):02d}:{s:06.3f}"

    def __sub__(self, other):
        return MockTimecode(self._seconds - other._seconds)

    @property
    def seconds(self):
        return self._seconds


class TestMergeShortScenes(unittest.TestCase):
    def test_empty_list(self):
        result = merge_short_scenes([])
        self.assertEqual(result, [])

    def test_no_merge_needed(self):
        scenes = [
            (MockTimecode(0), MockTimecode(3)),
            (MockTimecode(3), MockTimecode(6)),
            (MockTimecode(6), MockTimecode(9)),
        ]
        result = merge_short_scenes(scenes, min_duration_sec=1.0)
        self.assertEqual(len(result), 3)

    def test_merge_short_middle(self):
        scenes = [
            (MockTimecode(0), MockTimecode(0.3)),   # 短: 0.3s，会被并入
            (MockTimecode(0.3), MockTimecode(3)),
            (MockTimecode(3), MockTimecode(6)),
        ]
        result = merge_short_scenes(scenes, min_duration_sec=1.0)
        self.assertEqual(len(result), 2)
        self.assertAlmostEqual(result[0][0].get_seconds(), 0.0)
        self.assertAlmostEqual(result[0][1].get_seconds(), 3.0)

    def test_merge_short_last(self):
        scenes = [
            (MockTimecode(0), MockTimecode(3)),
            (MockTimecode(3), MockTimecode(6)),
            (MockTimecode(6), MockTimecode(6.2)),   # 短: 0.2s
        ]
        result = merge_short_scenes(scenes, min_duration_sec=1.0)
        self.assertEqual(len(result), 2)
        self.assertAlmostEqual(result[-1][1].get_seconds(), 6.2)

    def test_single_scene(self):
        scenes = [(MockTimecode(0), MockTimecode(5))]
        result = merge_short_scenes(scenes, min_duration_sec=1.0)
        self.assertEqual(len(result), 1)


class TestDefaultThresholds(unittest.TestCase):
    def test_default_values(self):
        self.assertEqual(DEFAULT_THRESHOLDS["content"], 27.0)
        self.assertEqual(DEFAULT_THRESHOLDS["adaptive"], 3.0)
        self.assertEqual(DEFAULT_THRESHOLDS["threshold"], 12.0)


if __name__ == "__main__":
    unittest.main()
