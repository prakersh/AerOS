"""Groq Whisper ASR provider."""

import io
from typing import Any

from openai import AsyncOpenAI

from aeros.ai.base import ASRResponse


class GroqASRProvider:
    def __init__(self, api_key: str, model: str = "whisper-large-v3-turbo"):
        self._client = AsyncOpenAI(
            base_url="https://api.groq.com/openai/v1",
            api_key=api_key,
        )
        self._default_model = model

    async def transcribe(
        self,
        audio_data: bytes,
        *,
        model: str | None = None,
        language: str | None = None,
    ) -> ASRResponse:
        audio_file = io.BytesIO(audio_data)
        audio_file.name = "audio.webm"

        kwargs: dict[str, Any] = {
            "model": model or self._default_model,
            "file": audio_file,
        }
        if language:
            kwargs["language"] = language

        resp = await self._client.audio.transcriptions.create(**kwargs)
        return ASRResponse(
            text=resp.text,
            language=language or "",
            duration_seconds=getattr(resp, "duration", 0) or 0,
        )
