import unittest
from unittest.mock import patch, MagicMock
from ryan_comfy_utils.nodes.llm_nodes import RyanLLMChat, RyanLLMVisionChat


class TestLLMNodes(unittest.TestCase):
    @patch("ryan_comfy_utils.core.llm_client.OpenAI")
    @patch("ryan_comfy_utils.core.llm_client.resolve_profile")
    def test_llm_chat_disable_thinking(self, mock_resolve_profile, mock_openai_class):
        mock_resolve_profile.return_value = {
            "api_key": "test_key",
            "base_url": "https://api.test.com/v1",
            "model": "test-model"
        }
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Hello there"
        mock_response.model_dump.return_value = {"choices": []}
        mock_client.chat.completions.create.return_value = mock_response

        node = RyanLLMChat()
        # Test with disable_thinking = True
        node.run(
            profile="default",
            model_override="",
            system_prompt="sys",
            user_prompt="usr",
            temperature=0.7,
            max_tokens=100,
            top_p=1.0,
            timeout_seconds=30,
            retry_count=0,
            disable_thinking=True,
            extra_body_json=""
        )

        mock_client.chat.completions.create.assert_called_once()
        called_kwargs = mock_client.chat.completions.create.call_args.kwargs
        self.assertIn("extra_body", called_kwargs)
        self.assertEqual(called_kwargs["extra_body"]["enable_thinking"], False)
        self.assertEqual(called_kwargs["extra_body"]["reasoning"], {"exclude": True})

    @patch("ryan_comfy_utils.core.llm_client.OpenAI")
    @patch("ryan_comfy_utils.core.llm_client.resolve_profile")
    def test_llm_chat_enable_thinking_default(self, mock_resolve_profile, mock_openai_class):
        mock_resolve_profile.return_value = {
            "api_key": "test_key",
            "base_url": "https://api.test.com/v1",
            "model": "test-model"
        }
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Hello there"
        mock_response.model_dump.return_value = {"choices": []}
        mock_client.chat.completions.create.return_value = mock_response

        node = RyanLLMChat()
        # Test with disable_thinking = False
        node.run(
            profile="default",
            model_override="",
            system_prompt="sys",
            user_prompt="usr",
            temperature=0.7,
            max_tokens=100,
            top_p=1.0,
            timeout_seconds=30,
            retry_count=0,
            disable_thinking=False,
            extra_body_json=""
        )

        mock_client.chat.completions.create.assert_called_once()
        called_kwargs = mock_client.chat.completions.create.call_args.kwargs
        self.assertNotIn("extra_body", called_kwargs)


if __name__ == "__main__":
    unittest.main()
