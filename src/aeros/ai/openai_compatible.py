"""OpenAI-compatible provider — works with MiniMax, NVIDIA NIM, OpenAI, Azure, etc."""

import base64
import re
import time
import uuid
from typing import Any

import structlog
from openai import AsyncOpenAI

_THINK_RE = re.compile(r"<think>.*?</think>\s*", re.DOTALL)
_CODE_FENCE_RE = re.compile(r"```(?:json)?\s*\n?(.*?)\n?```", re.DOTALL)


def _clean_llm_content(raw: str) -> str:
    """Strip reasoning tags and markdown code fences from model output."""
    text = _THINK_RE.sub("", raw).strip()
    m = _CODE_FENCE_RE.search(text)
    if m:
        text = m.group(1).strip()
    return text

from aeros.ai.base import (
    ChatMessage,
    ChatResponse,
    EmbeddingResponse,
    VisionResponse,
)

logger = structlog.get_logger()


def _log_llm_call(
    trace_id: str,
    provider: str,
    model: str,
    prompt_tokens: int,
    completion_tokens: int,
    latency_ms: int,
    status: str = "success",
    error_message: str | None = None,
    rfx_id: int | None = None,
    user_id: int | None = None,
) -> None:
    try:
        from sqlmodel import Session

        from aeros.db import engine
        from aeros.models.observability import LLMCallLog

        from aeros.ai.pricing import estimate_cost

        total_tokens = prompt_tokens + completion_tokens
        estimated_cost = estimate_cost(model, prompt_tokens, completion_tokens)

        with Session(engine) as session:
            log = LLMCallLog(
                trace_id=trace_id,
                provider=provider,
                model=model,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                latency_ms=latency_ms,
                estimated_cost_usd=estimated_cost,
                status=status,
                error_message=error_message,
                rfx_id=rfx_id,
                user_id=user_id,
            )
            session.add(log)
            session.commit()
    except Exception as e:
        logger.warning("observability.log_failed", error=str(e))


class OpenAICompatibleProvider:
    def __init__(self, base_url: str, api_key: str, default_model: str = ""):
        self._client = AsyncOpenAI(base_url=base_url, api_key=api_key)
        self._default_model = default_model
        self._provider_name = base_url.split("//")[-1].split("/")[0]
        self.user_id: int | None = None
        self.rfx_id: int | None = None

    async def chat(
        self,
        messages: list[ChatMessage],
        *,
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 16384,
        response_format: dict[str, Any] | None = None,
        user_id: int | None = None,
        rfx_id: int | None = None,
    ) -> ChatResponse:
        _uid = user_id if user_id is not None else self.user_id
        _rfx = rfx_id if rfx_id is not None else self.rfx_id
        kwargs: dict[str, Any] = {
            "model": model or self._default_model,
            "messages": [m.model_dump() for m in messages],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if response_format:
            kwargs["response_format"] = response_format

        trace_id = uuid.uuid4().hex[:16]
        t0 = time.monotonic()
        status = "success"
        error_msg = None

        try:
            resp = await self._client.chat.completions.create(**kwargs)
        except Exception as e:
            status = "error"
            error_msg = str(e)
            latency_ms = int((time.monotonic() - t0) * 1000)
            _log_llm_call(
                trace_id,
                self._provider_name,
                kwargs["model"],
                0,
                0,
                latency_ms,
                status,
                error_msg,
                rfx_id=_rfx,
                user_id=_uid,
            )
            raise

        latency_ms = int((time.monotonic() - t0) * 1000)
        choice = resp.choices[0]
        usage = resp.usage

        prompt_tokens = usage.prompt_tokens if usage else 0
        completion_tokens = usage.completion_tokens if usage else 0
        _log_llm_call(
            trace_id,
            self._provider_name,
            resp.model or kwargs["model"],
            prompt_tokens,
            completion_tokens,
            latency_ms,
            rfx_id=_rfx,
            user_id=_uid,
        )

        content = _clean_llm_content(choice.message.content or "")

        return ChatResponse(
            content=content,
            input_tokens=prompt_tokens,
            output_tokens=completion_tokens,
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

        vision_messages: list[dict[str, Any]] = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": data_url}},
                ],
            }
        ]

        used_model = model or self._default_model
        trace_id = uuid.uuid4().hex[:16]
        t0 = time.monotonic()

        try:
            resp = await self._client.chat.completions.create(
                model=used_model,
                messages=vision_messages,  # type: ignore[arg-type]
                max_tokens=4096,
                temperature=0.1,
            )
        except Exception as e:
            latency_ms = int((time.monotonic() - t0) * 1000)
            _log_llm_call(
                trace_id, self._provider_name, used_model, 0, 0, latency_ms, "error", str(e)
            )
            raise

        latency_ms = int((time.monotonic() - t0) * 1000)
        choice = resp.choices[0]
        usage = resp.usage

        prompt_tokens = usage.prompt_tokens if usage else 0
        completion_tokens = usage.completion_tokens if usage else 0
        _log_llm_call(
            trace_id,
            self._provider_name,
            resp.model or used_model,
            prompt_tokens,
            completion_tokens,
            latency_ms,
        )

        content = _clean_llm_content(choice.message.content or "")

        return VisionResponse(
            content=content,
            input_tokens=prompt_tokens,
            output_tokens=completion_tokens,
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
