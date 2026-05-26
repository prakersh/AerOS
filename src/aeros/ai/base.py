"""Provider protocols for AI backends."""

from typing import Protocol, runtime_checkable

from pydantic import BaseModel


class ChatMessage(BaseModel):
    role: str  # system, user, assistant
    content: str | list[dict]


class ChatResponse(BaseModel):
    content: str
    input_tokens: int = 0
    output_tokens: int = 0
    model: str = ""
    finish_reason: str = ""


class VisionResponse(BaseModel):
    content: str
    input_tokens: int = 0
    output_tokens: int = 0
    model: str = ""


class ASRResponse(BaseModel):
    text: str
    language: str = ""
    duration_seconds: float = 0


class EmbeddingResponse(BaseModel):
    embedding: list[float]
    model: str = ""
    input_tokens: int = 0


@runtime_checkable
class ChatProvider(Protocol):
    async def chat(
        self,
        messages: list[ChatMessage],
        *,
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        response_format: dict | None = None,
    ) -> ChatResponse: ...


@runtime_checkable
class VisionProvider(Protocol):
    async def vision(
        self,
        image_data: bytes,
        prompt: str,
        *,
        model: str | None = None,
        mime_type: str = "image/jpeg",
    ) -> VisionResponse: ...


@runtime_checkable
class ASRProvider(Protocol):
    async def transcribe(
        self,
        audio_data: bytes,
        *,
        model: str | None = None,
        language: str | None = None,
    ) -> ASRResponse: ...


@runtime_checkable
class EmbeddingProvider(Protocol):
    async def embed(
        self,
        texts: list[str],
        *,
        model: str | None = None,
    ) -> list[EmbeddingResponse]: ...
