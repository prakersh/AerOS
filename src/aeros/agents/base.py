"""Base agent class for all AEROS agents."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

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
    metadata: dict = field(default_factory=dict)


@dataclass
class AgentResult:
    message: str
    data: dict = field(default_factory=dict)
    tool_calls: list[dict] = field(default_factory=list)
    success: bool = True


class BaseAgent(ABC):
    name: str = "base"

    @abstractmethod
    async def run(self, ctx: AgentContext, user_input: str) -> AgentResult:
        ...
