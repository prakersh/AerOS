"""VendorCopilotAgent — helps vendors compose RFQ responses."""

from aeros.agents.base import AgentContext, AgentResult, BaseAgent, parse_llm_json
from aeros.ai.base import ChatMessage

VENDOR_SYSTEM_PROMPT = """You are the AEROS Vendor Co-pilot. \
You help vendors respond to procurement requests (RFQs).

Your capabilities:
- Help vendors understand RFQ requirements
- Suggest pricing based on their historical rates
- Help compose professional reply messages
- Guide them through the upload process for rate cards/quotations

Always respond in JSON format:
{
  "message": "your response to the vendor",
  "suggestions": ["optional list of suggested actions"],
  "status": "chatting" | "ready_to_reply"
}

Be concise, professional, and helpful. Support Hindi/Hinglish if the vendor writes in it."""


class VendorCopilotAgent(BaseAgent):
    """AI co-pilot that assists vendors with composing RFQ replies."""

    name = "vendor_copilot"

    async def run(self, ctx: AgentContext, user_input: str) -> AgentResult:
        """Process vendor input and return AI-assisted guidance.

        Args:
            ctx: Agent context with session, provider, and metadata.
            user_input: The vendor's message text.

        Returns:
            AgentResult with parsed JSON data containing message,
            suggestions, and status.
        """
        history: list[dict[str, str]] = ctx.metadata.get("history", [])
        rfx_context: str = ctx.metadata.get("rfx_context", "")

        messages: list[ChatMessage] = [
            ChatMessage(role="system", content=VENDOR_SYSTEM_PROMPT),
        ]
        if rfx_context:
            messages.append(ChatMessage(role="system", content=f"RFQ DETAILS:\n{rfx_context}"))

        for h in history:
            messages.append(ChatMessage(role=h["role"], content=h["content"]))

        messages.append(ChatMessage(role="user", content=user_input))

        response = await ctx.chat_provider.chat(
            messages,
            temperature=0.3,
            max_tokens=16384,
            response_format={"type": "json_object"},
        )

        parsed = parse_llm_json(
            response.content, {"message": response.content, "status": "chatting"}
        )

        return AgentResult(
            message=parsed.get("message", response.content),
            data=parsed,
            success=True,
        )
