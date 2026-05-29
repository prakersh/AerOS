"""Base agent class for all AEROS agents."""

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from sqlmodel import Session

from aeros.ai.openai_compatible import OpenAICompatibleProvider
from aeros.security.auth_context import AuthContext


@dataclass
class AgentContext:
    session: Session
    caller: AuthContext
    chat_provider: OpenAICompatibleProvider
    vision_provider: OpenAICompatibleProvider | None = None
    rfx_id: int | None = None
    thread_id: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentResult:
    message: str
    data: dict[str, Any] = field(default_factory=dict)
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    success: bool = True


def parse_llm_json(raw: str, fallback: dict[str, Any] | None = None) -> dict[str, Any]:
    try:
        return json.loads(raw)  # type: ignore[no-any-return]
    except json.JSONDecodeError:
        return fallback if fallback is not None else {"message": raw}


class BaseAgent(ABC):
    name: str = "base"

    @abstractmethod
    async def run(self, ctx: AgentContext, user_input: str) -> AgentResult: ...
