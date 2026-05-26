"""OpenAI-compatible provider — works with NVIDIA NIM, OpenAI, Azure, etc."""

import base64

from openai import AsyncOpenAI

from aeros.ai.base import (
    ASRResponse,
    ChatMessage,
    ChatResponse,
    EmbeddingResponse,
    VisionResponse,
)


class OpenAICompatibleProvider:
    def __init__(self, base_url: str, api_key: str, default_model: str = ""):
        self._client = AsyncOpenAI(base_url=base_url, api_key=api_key)
        self._default_model = default_model

    async def chat(
        self,
        messages: list[ChatMessage],
        *,
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        response_format: dict | None = None,
    ) -> ChatResponse:
        kwargs: dict = {
            "model": model or self._default_model,
            "messages": [m.model_dump() for m in messages],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if response_format:
            kwargs["response_format"] = response_format

        resp = await self._client.chat.completions.create(**kwargs)
        choice = resp.choices[0]
        usage = resp.usage
        return ChatResponse(
            content=choice.message.content or "",
            input_tokens=usage.prompt_tokens if usage else 0,
            output_tokens=usage.completion_tokens if usage else 0,
            model=resp.model or kwargs["model"],
            finish_reason=choice.finish_reason or "",
        )

    async def vision(
        self,
        image_data: bytes,
        prompt: str,
        *,
        model: str | None = None,
        mime_type: str = "image/jpeg",
    ) -> VisionResponse:
        b64 = base64.b64encode(image_data).decode()
        data_url = f"data:{mime_type};base64,{b64}"

        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": data_url}},
                ],
            }
        ]
        resp = await self._client.chat.completions.create(
            model=model or self._default_model,
            messages=messages,
            max_tokens=4096,
            temperature=0.1,
        )
        choice = resp.choices[0]
        usage = resp.usage
        return VisionResponse(
            content=choice.message.content or "",
            input_tokens=usage.prompt_tokens if usage else 0,
            output_tokens=usage.completion_tokens if usage else 0,
            model=resp.model or "",
        )

    async def embed(
        self,
        texts: list[str],
        *,
        model: str | None = None,
    ) -> list[EmbeddingResponse]:
        resp = await self._client.embeddings.create(
            model=model or self._default_model,
            input=texts,
        )
        results = []
        for item in resp.data:
            results.append(
                EmbeddingResponse(
                    embedding=item.embedding,
                    model=resp.model or "",
                    input_tokens=resp.usage.prompt_tokens if resp.usage else 0,
                )
            )
        return results
