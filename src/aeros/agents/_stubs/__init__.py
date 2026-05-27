"""Stub agents for Coming Soon features."""

from aeros.agents.base import AgentContext, AgentResult, BaseAgent


class NegotiationAgent(BaseAgent):
    """Placeholder for the negotiation agent (coming soon)."""

    name = "negotiation"

    async def run(self, ctx: AgentContext, user_input: str) -> AgentResult:
        return AgentResult(
            message="Negotiation agent coming soon.",
            data={"status": "coming_soon"},
            success=False,
        )


class ContractAgent(BaseAgent):
    """Placeholder for the contract agent (coming soon)."""

    name = "contract"

    async def run(self, ctx: AgentContext, user_input: str) -> AgentResult:
        return AgentResult(
            message="Contract agent coming soon.",
            data={"status": "coming_soon"},
            success=False,
        )


class InvoiceAgent(BaseAgent):
    """Placeholder for the invoice agent (coming soon)."""

    name = "invoice"

    async def run(self, ctx: AgentContext, user_input: str) -> AgentResult:
        return AgentResult(
            message="Invoice agent coming soon.",
            data={"status": "coming_soon"},
            success=False,
        )


class AnalyticsAgent(BaseAgent):
    """Placeholder for the analytics agent (coming soon)."""

    name = "analytics"

    async def run(self, ctx: AgentContext, user_input: str) -> AgentResult:
        return AgentResult(
            message="Analytics agent coming soon.",
            data={"status": "coming_soon"},
            success=False,
        )
