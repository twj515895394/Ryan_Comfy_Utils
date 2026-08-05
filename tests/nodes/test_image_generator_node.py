import unittest
from unittest.mock import patch, MagicMock
import io
import json
import urllib.error
import torch
from PIL import Image

from ryan_comfy_utils.nodes.image_generator_node import RyanImageGenerator


class TestImageGeneratorNode(unittest.TestCase):
    def test_input_types(self):
        inputs = RyanImageGenerator.INPUT_TYPES()
        required = inputs["required"]
        optional = inputs["optional"]

        self.assertIn("profile", required)
        self.assertIn("prompt", required)
        self.assertIn("size", required)
        self.assertIn("number_of_images", required)
        self.assertIn("response_format", required)
        self.assertIn("extra_body_json", required)
        
        # Verify optional inputs have image_01 to image_10 slots
        self.assertIn("image_01", optional)
        self.assertIn("image_02", optional)
        self.assertIn("image_slot_count", optional)

    @patch("urllib.request.urlopen")
    @patch("ryan_comfy_utils.nodes.image_generator_node.resolve_profile")
    def test_generate_b64_json(self, mock_resolve_profile, mock_urlopen):
        # Mock profile resolution
        mock_resolve_profile.return_value = {
            "api_key": "test_key",
            "base_url": "https://api.openai.com/v1",
            "model": "dall-e-3",
        }

        # Mock API response returning a 1x1 white PNG base64
        import base64
        png_bytes = io.BytesIO()
        Image.new("RGB", (1, 1), "white").save(png_bytes, format="PNG")
        b64_png = base64.b64encode(png_bytes.getvalue()).decode("utf-8")
        response_json = {
            "created": 123456789,
            "data": [
                {"b64_json": b64_png}
            ]
        }
        
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(response_json).encode("utf-8")
        mock_urlopen.return_value.__enter__.return_value = mock_response

        # Execute node
        node = RyanImageGenerator()
        result = node.generate(
            profile="test_profile",
            model_override="",
            prompt="A beautiful sunrise",
            size="512x512",
            custom_width=512,
            custom_height=512,
            number_of_images=1,
            response_format="b64_json",
            extra_body_json="",
            image_slot_count=2,
            image_01=None,
            image_02=None,
        )

        # Verify output shape and type
        self.assertEqual(len(result), 1)
        output_tensor = result[0]
        self.assertTrue(isinstance(output_tensor, torch.Tensor))
        # Batch of 1 image, height 1, width 1, channel 3
        self.assertEqual(output_tensor.shape, (1, 1, 1, 3))
        # Value is white, so it should be close to 1.0
        self.assertAlmostEqual(output_tensor[0, 0, 0, 0].item(), 1.0, places=2)

    @patch("urllib.request.urlopen")
    @patch("ryan_comfy_utils.nodes.image_generator_node.resolve_profile")
    def test_generate_with_images(self, mock_resolve_profile, mock_urlopen):
        mock_resolve_profile.return_value = {
            "api_key": "test_key",
            "base_url": "https://api.openai.com/v1",
            "model": "dall-e-3",
        }

        # Mock API response
        import base64
        png_bytes = io.BytesIO()
        Image.new("RGB", (1, 1), "white").save(png_bytes, format="PNG")
        b64_png = base64.b64encode(png_bytes.getvalue()).decode("utf-8")
        response_json = {
            "data": [{"b64_json": b64_png}]
        }
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(response_json).encode("utf-8")
        mock_urlopen.return_value.__enter__.return_value = mock_response

        # Create input image tensor [1, 64, 64, 3]
        input_image = torch.ones((1, 64, 64, 3), dtype=torch.float32)

        node = RyanImageGenerator()
        result = node.generate(
            profile="test_profile",
            model_override="",
            prompt="Modify this image to be red",
            size="1024x1024",
            custom_width=1024,
            custom_height=1024,
            number_of_images=1,
            response_format="auto",
            extra_body_json="",
            image_slot_count=1,
            image_01=input_image,
        )

        # Verify API request payload had "images" key in it
        args, kwargs = mock_urlopen.call_args
        req = args[0]
        self.assertTrue(isinstance(req, urllib.request.Request))
        req_body = json.loads(req.data.decode("utf-8"))
        self.assertIn("images", req_body)
        self.assertEqual(len(req_body["images"]), 1)

    @patch("urllib.request.urlopen")
    @patch("ryan_comfy_utils.nodes.image_generator_node.resolve_profile")
    def test_generate_url(self, mock_resolve_profile, mock_urlopen):
        # Mock profile resolution
        mock_resolve_profile.return_value = {
            "api_key": "test_key",
            "base_url": "https://api.openai.com/v1",
            "model": "dall-e-3",
        }

        # 1x1 white PNG raw bytes
        png_bytes = base64_bytes = io.BytesIO()
        Image.new("RGB", (1, 1), "white").save(png_bytes, format="PNG")
        png_raw_data = png_bytes.getvalue()

        # Mock first urlopen for API response, second urlopen for downloading the image
        mock_api_response = MagicMock()
        mock_api_response.read.return_value = json.dumps({
            "data": [{"url": "https://fakeurl.com/image.png"}]
        }).encode("utf-8")
        
        mock_img_response = MagicMock()
        mock_img_response.read.return_value = png_raw_data

        # Configure urlopen mock to return API response then the image bytes
        mock_urlopen.side_effect = [
            MagicMock(__enter__=MagicMock(return_value=mock_api_response)),
            MagicMock(__enter__=MagicMock(return_value=mock_img_response))
        ]

        # Execute node
        node = RyanImageGenerator()
        result = node.generate(
            profile="test_profile",
            model_override="",
            prompt="A beautiful sunrise",
            size="custom",
            custom_width=256,
            custom_height=256,
            number_of_images=1,
            response_format="url",
            extra_body_json="",
            image_slot_count=2,
            image_01=None,
            image_02=None,
        )

        # Verify output shape and type
        self.assertEqual(len(result), 1)
        output_tensor = result[0]
        self.assertTrue(isinstance(output_tensor, torch.Tensor))
        self.assertEqual(output_tensor.shape, (1, 1, 1, 3))


if __name__ == "__main__":
    unittest.main()
