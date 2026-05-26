"""IntakeAgent — conversational RFx drafting with AI co-pilot."""

import json

from sqlmodel import select

from aeros.agents.base import AgentContext, AgentResult, BaseAgent
from aeros.ai.base import ChatMessage
from aeros.ai.prompts.intake import INTAKE_SYSTEM_PROMPT
from aeros.ai.schemas import RFxDraft
from aeros.models.sku import SKU
from aeros.models.vendor import Vendor
from aeros.models.user_defaults import UserDefaults
from aeros.services import inventory_service, vendor_service


class IntakeAgent(BaseAgent):
    name = "intake"

    async def run(self, ctx: AgentContext, user_input: str) -> AgentResult:
        org_id = ctx.caller.org_id or 0

        # Gather context for the LLM
        skus = inventory_service.list_skus(ctx.session, org_id)
        sku_list = [
            {"id": s.id, "code": s.code, "name": s.name, "unit": s.unit,
             "last_price": s.last_price, "category_id": s.category_id}
            for s in skus
        ]

        vendors = vendor_service.list_vendors(ctx.session, org_id)
        vendor_list = [
            {"id": v.id, "name": v.name, "email": v.primary_email,
             "categories": v.category_ids_csv, "score": v.performance_score,
             "has_telegram": bool(v.telegram_chat_id),
             "has_user_account": bool(v.vendor_user_id)}
            for v in vendors
        ]

        # Get user defaults
        defaults = ctx.session.exec(
            select(UserDefaults).where(UserDefaults.user_id == ctx.caller.user_id)
        ).first()
        defaults_info = {}
        if defaults:
            defaults_info = {
                "payment_terms": defaults.payment_terms_default,
                "delivery_terms": defaults.delivery_terms_default,
                "quote_validity_days": defaults.quote_validity_days_default,
                "currency": defaults.currency_default,
                "tax_treatment": defaults.tax_treatment_default,
                "delivery_window": defaults.delivery_window_default,
            }

        # Get conversation history from metadata
        history: list[dict] = ctx.metadata.get("history", [])

        messages = [
            ChatMessage(role="system", content=INTAKE_SYSTEM_PROMPT),
            ChatMessage(
                role="system",
                content=f"INVENTORY (available SKUs):\n{json.dumps(sku_list, indent=2)}"
            ),
            ChatMessage(
                role="system",
                content=f"VENDOR DIRECTORY:\n{json.dumps(vendor_list, indent=2)}"
            ),
            ChatMessage(
                role="system",
                content=f"BUYER DEFAULT TERMS:\n{json.dumps(defaults_info, indent=2)}"
            ),
        ]

        for h in history:
            messages.append(ChatMessage(role=h["role"], content=h["content"]))

        messages.append(ChatMessage(role="user", content=user_input))

        response = await ctx.chat_provider.chat(
            messages,
            temperature=0.3,
            max_tokens=2048,
            response_format={"type": "json_object"},
        )

        try:
            parsed = json.loads(response.content)
        except json.JSONDecodeError:
            parsed = {"message": response.content, "status": "gathering"}

        return AgentResult(
            message=parsed.get("message", response.content),
            data=parsed,
            success=True,
        )
