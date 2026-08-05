import unittest
from unittest.mock import patch, MagicMock
import io
import json
import urllib.error
import torch
from PIL import Image

from ryan_comfy_utils.nodes.video_generator_node import RyanVideoGenerator


class TestVideoGeneratorNode(unittest.TestCase):
    def test_input_types(self):
        inputs = RyanVideoGenerator.INPUT_TYPES()
        required = inputs["required"]
        optional = inputs["optional"]

        self.assertIn("profile", required)
        self.assertIn("prompt", required)
        self.assertIn("aspect_ratio", required)
        self.assertIn("resolution", required)
        self.assertIn("duration", required)
        self.assertIn("polling_interval", required)
        self.assertIn("extra_body_json", required)
        
        self.assertIn("image_01", optional)
        self.assertIn("image_slot_count", optional)

    @patch("ryan_comfy_utils.nodes.video_generator_node.load_video_frames")
    @patch("urllib.request.urlopen")
    @patch("ryan_comfy_utils.nodes.video_generator_node.resolve_profile")
    def test_generate_text_to_video(self, mock_resolve_profile, mock_urlopen, mock_load_video_frames):
        # Mock profile resolution
        mock_resolve_profile.return_value = {
            "api_key": "test_key",
            "base_url": "http://localhost:8317/v1",
            "model": "grok-imagine-video",
        }

        # Mock submission response: request_id
        mock_submit_resp = MagicMock()
        mock_submit_resp.read.return_value = json.dumps({
            "request_id": "test-req-id"
        }).encode("utf-8")

        # Mock first polling response (pending)
        mock_poll_resp_1 = MagicMock()
        mock_poll_resp_1.read.return_value = json.dumps({
            "status": "pending",
            "progress": 50
        }).encode("utf-8")

        # Mock second polling response (done)
        mock_poll_resp_2 = MagicMock()
        mock_poll_resp_2.read.return_value = json.dumps({
            "status": "done",
            "progress": 100,
            "video": {"url": "https://fakeurl.com/download.mp4"}
        }).encode("utf-8")

        # Mock download response
        mock_download_resp = MagicMock()
        mock_download_resp.read.return_value = b"fake-mp4-binary-data"

        # Set up mock urlopen calls
        mock_urlopen.side_effect = [
            MagicMock(__enter__=MagicMock(return_value=mock_submit_resp)),   # submit
            MagicMock(__enter__=MagicMock(return_value=mock_poll_resp_1)),  # poll 1
            MagicMock(__enter__=MagicMock(return_value=mock_poll_resp_2)),  # poll 2
            MagicMock(__enter__=MagicMock(return_value=mock_download_resp))  # download
        ]

        # Mock load_video_frames returning 10 fake frames [10, 64, 64, 3]
        fake_tensor = torch.ones((10, 64, 64, 3), dtype=torch.float32)
        mock_load_video_frames.return_value = (fake_tensor, 10)

        # Run generate node
        node = RyanVideoGenerator()
        result = node.generate(
            profile="grok-imagine-video",
            model_override="",
            prompt="A puppy playing in the rain",
            aspect_ratio="16:9",
            resolution="720p",
            duration=5,
            polling_interval=1,
            extra_body_json="",
            image_slot_count=2,
            image_01=None,
            image_02=None,
        )

        # Verify output formats
        self.assertIn("ui", result)
        self.assertIn("result", result)
        out_tensor, out_path = result["result"]
        self.assertTrue(isinstance(out_tensor, torch.Tensor))
        self.assertEqual(out_tensor.shape, (10, 64, 64, 3))
        self.assertTrue(isinstance(out_path, str))
        self.assertTrue(out_path.endswith(".mp4"))

        # Verify POST payload is text-to-video
        args, kwargs = mock_urlopen.call_args_list[0]
        req = args[0]
        req_body = json.loads(req.data.decode("utf-8"))
        self.assertNotIn("image", req_body)
        self.assertNotIn("reference_image_urls", req_body)
        self.assertEqual(req_body["model"], "grok-imagine-video")
        self.assertEqual(req_body["prompt"], "A puppy playing in the rain")

    @patch("ryan_comfy_utils.nodes.video_generator_node.load_video_frames")
    @patch("urllib.request.urlopen")
    @patch("ryan_comfy_utils.nodes.video_generator_node.resolve_profile")
    def test_generate_image_to_video_single(self, mock_resolve_profile, mock_urlopen, mock_load_video_frames):
        mock_resolve_profile.return_value = {
            "api_key": "test_key",
            "base_url": "http://localhost:8317/v1",
            "model": "grok-imagine-video",
        }

        # Mock api interactions
        mock_submit_resp = MagicMock()
        mock_submit_resp.read.return_value = json.dumps({"request_id": "test-req-id"}).encode("utf-8")
        mock_poll_resp = MagicMock()
        mock_poll_resp.read.return_value = json.dumps({
            "status": "done",
            "video": {"url": "https://fakeurl.com/download.mp4"}
        }).encode("utf-8")
        mock_download_resp = MagicMock()
        mock_download_resp.read.return_value = b"data"

        mock_urlopen.side_effect = [
            MagicMock(__enter__=MagicMock(return_value=mock_submit_resp)),
            MagicMock(__enter__=MagicMock(return_value=mock_poll_resp)),
            MagicMock(__enter__=MagicMock(return_value=mock_download_resp))
        ]

        fake_tensor = torch.ones((5, 32, 32, 3), dtype=torch.float32)
        mock_load_video_frames.return_value = (fake_tensor, 5)

        # 1 input image tensor
        input_image = torch.ones((1, 64, 64, 3), dtype=torch.float32)

        # Run generate node
        node = RyanVideoGenerator()
        result = node.generate(
            profile="grok-imagine-video",
            model_override="",
            prompt="Animate this puppy",
            aspect_ratio="16:9",
            resolution="720p",
            duration=5,
            polling_interval=1,
            extra_body_json="",
            image_slot_count=1,
            image_01=input_image,
        )

        # Verify POST payload is image-to-video (has "image" key containing "url")
        args, kwargs = mock_urlopen.call_args_list[0]
        req = args[0]
        req_body = json.loads(req.data.decode("utf-8"))
        self.assertIn("image", req_body)
        self.assertIn("url", req_body["image"])
        self.assertTrue(req_body["image"]["url"].startswith("data:image/jpeg;base64,"))
        self.assertNotIn("reference_image_urls", req_body)

    @patch("ryan_comfy_utils.nodes.video_generator_node.load_video_frames")
    @patch("urllib.request.urlopen")
    @patch("ryan_comfy_utils.nodes.video_generator_node.resolve_profile")
    def test_generate_reference_to_video_multiple(self, mock_resolve_profile, mock_urlopen, mock_load_video_frames):
        mock_resolve_profile.return_value = {
            "api_key": "test_key",
            "base_url": "http://localhost:8317/v1",
            "model": "grok-imagine-video",
        }

        # Mock api interactions
        mock_submit_resp = MagicMock()
        mock_submit_resp.read.return_value = json.dumps({"request_id": "test-req-id"}).encode("utf-8")
        mock_poll_resp = MagicMock()
        mock_poll_resp.read.return_value = json.dumps({
            "status": "done",
            "video": {"url": "https://fakeurl.com/download.mp4"}
        }).encode("utf-8")
        mock_download_resp = MagicMock()
        mock_download_resp.read.return_value = b"data"

        mock_urlopen.side_effect = [
            MagicMock(__enter__=MagicMock(return_value=mock_submit_resp)),
            MagicMock(__enter__=MagicMock(return_value=mock_poll_resp)),
            MagicMock(__enter__=MagicMock(return_value=mock_download_resp))
        ]

        fake_tensor = torch.ones((5, 32, 32, 3), dtype=torch.float32)
        mock_load_video_frames.return_value = (fake_tensor, 5)

        # 2 input image tensors
        input_image_1 = torch.ones((1, 64, 64, 3), dtype=torch.float32)
        input_image_2 = torch.ones((1, 64, 64, 3), dtype=torch.float32)

        # Run generate node
        node = RyanVideoGenerator()
        result = node.generate(
            profile="grok-imagine-video",
            model_override="",
            prompt="Combine @image1 character with @image2 setting",
            aspect_ratio="1:1",
            resolution="480p",
            duration=5,
            polling_interval=1,
            extra_body_json="",
            image_slot_count=2,
            image_01=input_image_1,
            image_02=input_image_2,
        )

        # Verify POST payload is reference-to-video (has "reference_image_urls" key)
        args, kwargs = mock_urlopen.call_args_list[0]
        req = args[0]
        req_body = json.loads(req.data.decode("utf-8"))
        self.assertNotIn("image", req_body)
        self.assertIn("reference_image_urls", req_body)
        self.assertEqual(len(req_body["reference_image_urls"]), 2)
        self.assertTrue(req_body["reference_image_urls"][0]["url"].startswith("data:image/jpeg;base64,"))
        self.assertTrue(req_body["reference_image_urls"][1]["url"].startswith("data:image/jpeg;base64,"))


if __name__ == "__main__":
    unittest.main()
