"""Tests for OpenAI-compatible provider (chat, vision, embedding)."""

from unittest.mock import AsyncMock, MagicMock, patch

from aeros.ai.base import ChatMessage
from aeros.ai.openai_compatible import OpenAICompatibleProvider


def _make_mock_response(content="test response", model="test-model", tokens_in=10, tokens_out=20):
    """Create a mock OpenAI chat completion response."""
    mock_resp = MagicMock()
    mock_resp.choices = [MagicMock()]
    mock_resp.choices[0].message.content = content
    mock_resp.choices[0].finish_reason = "stop"
    mock_resp.model = model
    mock_resp.usage = MagicMock()
    mock_resp.usage.prompt_tokens = tokens_in
    mock_resp.usage.completion_tokens = tokens_out
    return mock_resp


def _make_mock_embedding_response(model="embed-model", dim=4):
    """Create a mock OpenAI embedding response."""
    mock_resp = MagicMock()
    mock_resp.model = model
    mock_resp.data = [MagicMock()]
    mock_resp.data[0].embedding = [0.1] * dim
    mock_resp.usage = MagicMock()
    mock_resp.usage.prompt_tokens = 5
    return mock_resp


class TestChat:
    async def test_chat_returns_response(self):
        """Should return a ChatResponse with content and token counts."""
        provider = OpenAICompatibleProvider(
            base_url="http://test", api_key="key", default_model="model-1"
        )
        mock_resp = _make_mock_response(content="Hello world", tokens_in=15, tokens_out=25)

        with patch.object(provider._client.chat.completions, "create", new_callable=AsyncMock, return_value=mock_resp):
            messages = [ChatMessage(role="user", content="Hi")]
            result = await provider.chat(messages)

        assert result.content == "Hello world"
        assert result.input_tokens == 15
        assert result.output_tokens == 25

    async def test_chat_with_custom_model(self):
        """Should use custom model when provided."""
        provider = OpenAICompatibleProvider(
            base_url="http://test", api_key="key", default_model="default"
        )
        mock_resp = _make_mock_response()

        with patch.object(provider._client.chat.completions, "create", new_callable=AsyncMock, return_value=mock_resp) as mock_create:
            messages = [ChatMessage(role="user", content="test")]
            await provider.chat(messages, model="custom-model")

            call_kwargs = mock_create.call_args[1]
            assert call_kwargs["model"] == "custom-model"

    async def test_chat_with_response_format(self):
        """Should pass response_format when provided."""
        provider = OpenAICompatibleProvider(
            base_url="http://test", api_key="key", default_model="model"
        )
        mock_resp = _make_mock_response()

        with patch.object(provider._client.chat.completions, "create", new_callable=AsyncMock, return_value=mock_resp) as mock_create:
            messages = [ChatMessage(role="user", content="test")]
            await provider.chat(messages, response_format={"type": "json_object"})

            call_kwargs = mock_create.call_args[1]
            assert call_kwargs["response_format"] == {"type": "json_object"}

    async def test_chat_with_no_usage(self):
        """Should handle missing usage gracefully."""
        provider = OpenAICompatibleProvider(
            base_url="http://test", api_key="key", default_model="model"
        )
        mock_resp = _make_mock_response()
        mock_resp.usage = None

        with patch.object(provider._client.chat.completions, "create", new_callable=AsyncMock, return_value=mock_resp):
            messages = [ChatMessage(role="user", content="test")]
            result = await provider.chat(messages)

        assert result.input_tokens == 0
        assert result.output_tokens == 0


class TestVision:
    async def test_vision_returns_response(self):
        """Should return a VisionResponse with content."""
        provider = OpenAICompatibleProvider(
            base_url="http://test", api_key="key", default_model="vision-model"
        )
        mock_resp = _make_mock_response(content="Image description")

        with patch.object(provider._client.chat.completions, "create", new_callable=AsyncMock, return_value=mock_resp):
            result = await provider.vision(b"fake-image", "Describe this")

        assert result.content == "Image description"

    async def test_vision_custom_mime_type(self):
        """Should use custom mime type for data URL."""
        provider = OpenAICompatibleProvider(
            base_url="http://test", api_key="key", default_model="model"
        )
        mock_resp = _make_mock_response()

        with patch.object(provider._client.chat.completions, "create", new_callable=AsyncMock, return_value=mock_resp) as mock_create:
            await provider.vision(b"data", "prompt", mime_type="image/png")

            call_kwargs = mock_create.call_args[1]
            content = call_kwargs["messages"][0]["content"]
            image_url = content[1]["image_url"]["url"]
            assert "image/png" in image_url


class TestEmbed:
    async def test_embed_returns_embeddings(self):
        """Should return a list of EmbeddingResponse."""
        provider = OpenAICompatibleProvider(
            base_url="http://test", api_key="key", default_model="embed-model"
        )
        mock_resp = _make_mock_embedding_response(dim=8)

        with patch.object(provider._client.embeddings, "create", new_callable=AsyncMock, return_value=mock_resp):
            result = await provider.embed(["hello", "world"])

        assert len(result) == 1
        assert len(result[0].embedding) == 8
        assert result[0].input_tokens == 5
