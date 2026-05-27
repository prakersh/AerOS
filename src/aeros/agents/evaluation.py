"""EvaluationAgent — extracts offers from vendor attachments + email bodies."""

import json
from datetime import UTC, datetime

from sqlmodel import select

from aeros.agents.base import AgentContext, AgentResult, BaseAgent
from aeros.ai.base import ChatMessage
from aeros.ai.extractors.router import route_extraction
from aeros.ai.prompts.evaluation import EXTRACTION_SYSTEM_PROMPT, GLEANING_PROMPT
from aeros.ai.schemas import ExtractedOffer
from aeros.models.rfx import Attachment, ExtractionStatus, Message


class EvaluationAgent(BaseAgent):
    name = "evaluation"

    async def run(self, ctx: AgentContext, user_input: str) -> AgentResult:
        # user_input is the message_id to evaluate
        message_id = int(user_input)
        message = ctx.session.get(Message, message_id)
        if not message:
            return AgentResult(message="Message not found", success=False)

        # Collect all text snippets from this message
        snippets: list[str] = []

        # Email body / chat text
        if message.body_text and message.body_text.strip():
            snippets.append(f"[Email/Chat Body]\n{message.body_text}")

        # Attachments
        attachments = list(
            ctx.session.exec(
                select(Attachment).where(Attachment.message_id == message_id)
            ).all()
        )
        for att in attachments:
            try:
                text = await route_extraction(
                    att.storage_path,
                    att.mime_type,
                    vision_provider=ctx.vision_provider,
                )
                snippets.append(f"[{att.filename} ({att.mime_type})]\n{text}")
                att.extraction_status = ExtractionStatus.EXTRACTED
                att.extracted_at = datetime.now(UTC)
            except Exception as e:
                snippets.append(f"[{att.filename}] Extraction failed: {e}")
                att.extraction_status = ExtractionStatus.FAILED
                att.extraction_attempts += 1
            ctx.session.add(att)

        if not snippets:
            return AgentResult(message="No content to extract", success=False)

        combined = "\n\n---\n\n".join(snippets)

        # First pass extraction
        messages = [
            ChatMessage(role="system", content=EXTRACTION_SYSTEM_PROMPT),
            ChatMessage(
                role="user",
                content=f"Extract the structured offer from this vendor response:\n\n{combined}",
            ),
        ]
        response = await ctx.chat_provider.chat(
            messages,
            temperature=0.1,
            max_tokens=4096,
            response_format={"type": "json_object"},
        )

        # Gleaning pass (second review)
        gleaning_messages = [
            ChatMessage(role="system", content=EXTRACTION_SYSTEM_PROMPT),
            ChatMessage(
                role="user",
                content=GLEANING_PROMPT.format(
                    source_text=combined[:30000],
                    previous_extraction=response.content,
                ),
            ),
        ]
        gleaned = await ctx.chat_provider.chat(
            gleaning_messages,
            temperature=0.1,
            max_tokens=4096,
            response_format={"type": "json_object"},
        )

        try:
            offer_data = json.loads(gleaned.content)
        except json.JSONDecodeError:
            try:
                offer_data = json.loads(response.content)
            except json.JSONDecodeError:
                return AgentResult(
                    message="Failed to parse extraction result",
                    success=False,
                )

        # Validate via Pydantic
        try:
            extracted = ExtractedOffer(**offer_data)
        except Exception:
            extracted = ExtractedOffer(
                line_items=[],
                confidence_overall=0.0,
            )

        ctx.session.commit()

        return AgentResult(
            message=f"Extracted {len(extracted.line_items)} line items with {extracted.confidence_overall:.0%} confidence",
            data=offer_data,
            success=True,
        )
