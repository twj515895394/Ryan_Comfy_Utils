import sys
from unittest.mock import patch, MagicMock

# Mock ComfyUI modules before importing video_nodes to avoid ModuleNotFoundError
mock_folder_paths = MagicMock()
mock_folder_paths.get_temp_directory.return_value = "/tmp/comfy_temp"
sys.modules['folder_paths'] = mock_folder_paths
sys.modules['server'] = MagicMock()

import unittest
import torch
import numpy as np

from ryan_comfy_utils.nodes.video_nodes import RyanImageBatchSplitter


class TestImageSplitterNode(unittest.TestCase):
    def test_node_contract(self):
        node = RyanImageBatchSplitter()
        self.assertEqual(len(node.RETURN_TYPES), 12)
        self.assertEqual(node.RETURN_TYPES[0], "IMAGE")
        self.assertEqual(len(node.RETURN_NAMES), 12)
        self.assertEqual(node.RETURN_NAMES[0], "image_01")
        self.assertEqual(node.RETURN_NAMES[11], "image_12")

    @patch("PIL.Image.Image.save")
    def test_run_with_images(self, mock_save):
        # Create a mock batch of 3 images [3, 64, 64, 3]
        images_tensor = torch.zeros((3, 64, 64, 3))
        
        node = RyanImageBatchSplitter()
        out = node.run(images=images_tensor, output_count=4)
        
        # Check UI result
        self.assertIn("ui", out)
        self.assertIn("images", out["ui"])
        self.assertEqual(len(out["ui"]["images"]), 3)
        self.assertEqual(out["ui"]["images"][0]["type"], "temp")
        
        # Check result values
        self.assertIn("result", out)
        res_tuple = out["result"]
        self.assertEqual(len(res_tuple), 12)
        
        # First 3 should be tensors of shape [1, 64, 64, 3]
        for i in range(3):
            self.assertIsInstance(res_tuple[i], torch.Tensor)
            self.assertEqual(res_tuple[i].shape, (1, 64, 64, 3))
            
        # Remaining 9 should be None
        for i in range(3, 12):
            self.assertIsNone(res_tuple[i])

    def test_run_with_none(self):
        node = RyanImageBatchSplitter()
        out = node.run(images=None, output_count=4)
        self.assertIn("ui", out)
        self.assertEqual(out["ui"]["images"], [])
        self.assertIn("result", out)
        self.assertEqual(out["result"], (None,) * 12)


if __name__ == "__main__":
    unittest.main()
