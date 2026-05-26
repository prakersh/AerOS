"""Factory for AI providers — reads config, returns provider instances."""

from aeros.config import settings
from aeros.ai.openai_compatible import OpenAICompatibleProvider
from aeros.ai.groq_asr import GroqASRProvider


_NIM_BASE_URL = "https://integrate.api.nvidia.com/v1"


def get_chat_provider() -> OpenAICompatibleProvider:
    return OpenAICompatibleProvider(
        base_url=_NIM_BASE_URL,
        api_key=settings.nvidia_api_key,
        default_model=settings.default_chat_model,
    )


def get_vision_provider() -> OpenAICompatibleProvider:
    return OpenAICompatibleProvider(
        base_url=_NIM_BASE_URL,
        api_key=settings.nvidia_api_key,
        default_model=settings.default_vision_model,
    )


def get_embedding_provider() -> OpenAICompatibleProvider:
    return OpenAICompatibleProvider(
        base_url=_NIM_BASE_URL,
        api_key=settings.nvidia_api_key,
        default_model=settings.default_embed_model,
    )


def get_asr_provider() -> GroqASRProvider:
    return GroqASRProvider(api_key=settings.groq_api_key)
