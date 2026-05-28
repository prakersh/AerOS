"""Factory for AI providers — reads config, returns provider instances."""

from aeros.ai.groq_asr import GroqASRProvider
from aeros.ai.openai_compatible import OpenAICompatibleProvider
from aeros.config import settings


def get_chat_provider() -> OpenAICompatibleProvider:
    return OpenAICompatibleProvider(
        base_url=settings.mimo_base_url,
        api_key=settings.mimo_api_key,
        default_model=settings.default_chat_model,
    )


def get_vision_provider() -> OpenAICompatibleProvider:
    return OpenAICompatibleProvider(
        base_url=settings.mimo_base_url,
        api_key=settings.mimo_api_key,
        default_model=settings.default_vision_model,
    )


def get_embedding_provider() -> OpenAICompatibleProvider:
    return OpenAICompatibleProvider(
        base_url="https://integrate.api.nvidia.com/v1",
        api_key=settings.nvidia_api_key,
        default_model=settings.default_embed_model,
    )


def get_asr_provider() -> GroqASRProvider:
    return GroqASRProvider(api_key=settings.groq_api_key)
