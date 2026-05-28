"""Tests for Groq ASR provider."""

from unittest.mock import AsyncMock, MagicMock, patch

from aeros.ai.groq_asr import GroqASRProvider


class TestGroqASRProvider:
    def test_init(self):
        """Should initialize with API key and default model."""
        provider = GroqASRProvider(api_key="test-key")
        assert provider._default_model == "whisper-large-v3-turbo"

    def test_custom_model(self):
        """Should accept custom model."""
        provider = GroqASRProvider(api_key="key", model="whisper-v3")
        assert provider._default_model == "whisper-v3"

    async def test_transcribe_success(self):
        """Should return ASRResponse on successful transcription."""
        provider = GroqASRProvider(api_key="test-key")

        mock_resp = MagicMock()
        mock_resp.text = "Hello world, this is a test"
        mock_resp.duration = 5.2

        with patch.object(
            provider._client.audio.transcriptions,
            "create",
            new_callable=AsyncMock,
            return_value=mock_resp,
        ):
            result = await provider.transcribe(b"fake-audio-data")

        assert result.text == "Hello world, this is a test"
        assert result.duration_seconds == 5.2

    async def test_transcribe_with_language(self):
        """Should pass language parameter when provided."""
        provider = GroqASRProvider(api_key="test-key")

        mock_resp = MagicMock()
        mock_resp.text = "namaste"
        mock_resp.duration = 2.0

        with patch.object(
            provider._client.audio.transcriptions,
            "create",
            new_callable=AsyncMock,
            return_value=mock_resp,
        ) as mock_create:
            await provider.transcribe(b"audio", language="hi")
            call_kwargs = mock_create.call_args[1]
            assert call_kwargs["language"] == "hi"

    async def test_transcribe_without_language(self):
        """Should not pass language when not provided."""
        provider = GroqASRProvider(api_key="test-key")

        mock_resp = MagicMock()
        mock_resp.text = "test"
        mock_resp.duration = 1.0

        with patch.object(
            provider._client.audio.transcriptions,
            "create",
            new_callable=AsyncMock,
            return_value=mock_resp,
        ) as mock_create:
            await provider.transcribe(b"audio")
            call_kwargs = mock_create.call_args[1]
            assert "language" not in call_kwargs

    async def test_transcribe_no_duration(self):
        """Should handle missing duration attribute."""
        provider = GroqASRProvider(api_key="test-key")

        mock_resp = MagicMock()
        mock_resp.text = "test"
        del mock_resp.duration  # Simulate missing attribute

        with patch.object(
            provider._client.audio.transcriptions,
            "create",
            new_callable=AsyncMock,
            return_value=mock_resp,
        ):
            result = await provider.transcribe(b"audio")

        assert result.duration_seconds == 0
