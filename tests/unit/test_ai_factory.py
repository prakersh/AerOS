"""Tests for AI provider factory functions."""

from unittest.mock import patch


class TestAIFactory:
    def test_get_chat_provider(self):
        """Should return an OpenAICompatibleProvider for chat."""
        from aeros.ai.factory import get_chat_provider

        with patch("aeros.ai.factory.settings") as mock_settings:
            mock_settings.mimo_api_key = "test-key"
            mock_settings.mimo_base_url = "https://test.xiaomimimo.com/v1"
            mock_settings.default_chat_model = "test-model"
            provider = get_chat_provider()
            assert provider is not None

    def test_get_vision_provider(self):
        """Should return an OpenAICompatibleProvider for vision."""
        from aeros.ai.factory import get_vision_provider

        with patch("aeros.ai.factory.settings") as mock_settings:
            mock_settings.mimo_api_key = "test-key"
            mock_settings.mimo_base_url = "https://test.xiaomimimo.com/v1"
            mock_settings.default_vision_model = "test-model"
            provider = get_vision_provider()
            assert provider is not None

    def test_get_embedding_provider(self):
        """Should return an OpenAICompatibleProvider for embeddings."""
        from aeros.ai.factory import get_embedding_provider

        with patch("aeros.ai.factory.settings") as mock_settings:
            mock_settings.nvidia_api_key = "test-key"
            mock_settings.default_embed_model = "test-model"
            provider = get_embedding_provider()
            assert provider is not None

    def test_get_asr_provider(self):
        """Should return a GroqASRProvider."""
        from aeros.ai.factory import get_asr_provider

        with patch("aeros.ai.factory.settings") as mock_settings:
            mock_settings.groq_api_key = "test-key"
            provider = get_asr_provider()
            assert provider is not None
