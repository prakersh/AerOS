"""SourcingAgent — composes RFx messages, proposes dispatch plan (D35), dispatches on confirmation."""

import json

from sqlmodel import select

from aeros.agents.base import AgentContext, AgentResult, BaseAgent
from aeros.ai.base import ChatMessage
from aeros.channels.correlation import generate_correlation_token
from aeros.channels.email_out import send_rfx_invitation
from aeros.config import settings
from aeros.models.rfx import RFxLineItem, RFxRun, RFxVendor, Thread, Message
from aeros.models.vendor import Vendor
from aeros.services import rfx_service


SOURCING_SYSTEM_PROMPT = """You are the AEROS Sourcing Agent. Your job is to compose clear, professional vendor invitation messages for RFQs.

Given the RFx details and line items, compose a concise summary that vendors can understand and quote against.

OUTPUT (JSON):
{
  "subject": "Short subject line",
  "summary": "Multi-line summary of what's needed, including items, quantities, delivery window, and terms",
  "per_vendor_notes": {} // optional per-vendor customization
}
"""


class SourcingAgent(BaseAgent):
    name = "sourcing"

    async def run(self, ctx: AgentContext, user_input: str) -> AgentResult:
        action = json.loads(user_input) if user_input.startswith("{") else {"action": user_input}
        rfx_id = action.get("rfx_id") or ctx.rfx_id

        if not rfx_id:
            return AgentResult(message="No RFx ID provided", success=False)

        rfx = ctx.session.get(RFxRun, rfx_id)
        if not rfx:
            return AgentResult(message="RFx not found", success=False)

        line_items = list(
            ctx.session.exec(select(RFxLineItem).where(RFxLineItem.rfx_id == rfx_id)).all()
        )

        if action.get("action") == "propose_dispatch":
            return await self._propose_dispatch(ctx, rfx, line_items, action.get("vendor_ids", []))
        elif action.get("action") == "confirm_dispatch":
            return await self._confirm_dispatch(ctx, rfx, line_items, action.get("dispatch_plan", []))

        return AgentResult(message="Unknown action", success=False)

    async def _propose_dispatch(
        self, ctx: AgentContext, rfx: RFxRun, line_items: list, vendor_ids: list[int]
    ) -> AgentResult:
        dispatch_plan = []
        for vid in vendor_ids:
            vendor = ctx.session.get(Vendor, vid)
            if not vendor:
                continue

            # Channel priority: in-app > email > telegram (D35)
            if vendor.vendor_user_id:
                channel = "in_app"
                detail = "Active portal user"
            elif vendor.primary_email:
                channel = "email"
                detail = vendor.primary_email
            elif vendor.telegram_chat_id:
                channel = "telegram"
                detail = f"@{vendor.telegram_chat_id}"
            else:
                channel = "email"
                detail = vendor.primary_email

            dispatch_plan.append({
                "vendor_id": vendor.id,
                "vendor_name": vendor.name,
                "channel": channel,
                "channel_detail": detail,
            })

        return AgentResult(
            message="Here's the proposed dispatch plan. Confirm to send.",
            data={
                "dispatch_plan": dispatch_plan,
                "status": "confirming_dispatch",
            },
            success=True,
        )

    async def _confirm_dispatch(
        self, ctx: AgentContext, rfx: RFxRun, line_items: list, dispatch_plan: list
    ) -> AgentResult:
        # Compose the RFx summary via LLM
        items_text = "\n".join(
            f"- {li.qty} {li.unit_override or ''} (SKU ID: {li.sku_id})"
            for li in line_items
        )
        messages = [
            ChatMessage(role="system", content=SOURCING_SYSTEM_PROMPT),
            ChatMessage(role="user", content=f"""Compose an RFQ invitation for:
Title: {rfx.title}
Items:
{items_text}
Delivery: {rfx.delivery_window_start} to {rfx.delivery_window_end}
Deadline: {rfx.response_deadline}
Terms: {rfx.payment_terms_for_this_rfx}, {rfx.delivery_terms_for_this_rfx}
Currency: {rfx.currency_for_this_rfx}
"""),
        ]
        resp = await ctx.chat_provider.chat(
            messages, temperature=0.3, max_tokens=1024,
            response_format={"type": "json_object"},
        )
        try:
            composed = json.loads(resp.content)
        except json.JSONDecodeError:
            composed = {"subject": rfx.title, "summary": resp.content}

        summary = composed.get("summary", rfx.title)
        dispatched_count = 0

        for entry in dispatch_plan:
            vendor_id = entry["vendor_id"]
            channel = entry["channel"]
            vendor = ctx.session.get(Vendor, vendor_id)
            if not vendor:
                continue

            # Generate correlation token
            token, token_hash = generate_correlation_token(rfx.id, vendor_id)  # type: ignore[arg-type]

            # Create RFxVendor + Thread
            rfx_service.invite_vendor(ctx.session, rfx.id, vendor_id, token_hash)  # type: ignore[arg-type]

            portal_url = f"{settings.frontend_url}/vendor/rfx/{rfx.id}"

            # Dispatch based on channel
            if channel == "email" and vendor.primary_email:
                await send_rfx_invitation(
                    to_email=vendor.primary_email,
                    vendor_name=vendor.name,
                    rfx_title=rfx.title,
                    rfx_summary=summary,
                    correlation_token=token,
                    portal_url=portal_url,
                )
            # in_app: create a system message in the thread
            thread = ctx.session.exec(
                select(Thread).where(
                    Thread.rfx_id == rfx.id, Thread.vendor_id == vendor_id
                )
            ).first()
            if thread:
                sys_msg = Message(
                    thread_id=thread.id,  # type: ignore[arg-type]
                    sender_kind="system",
                    channel="system",
                    body_text=f"RFQ Invitation: {rfx.title}\n\n{summary}",
                )
                ctx.session.add(sys_msg)

            dispatched_count += 1

        # Update RFx status
        rfx_service.dispatch_rfx(ctx.session, rfx.id, ctx.caller.user_id)  # type: ignore[arg-type]
        ctx.session.commit()

        return AgentResult(
            message=f"RFQ dispatched to {dispatched_count} vendors!",
            data={"dispatched_count": dispatched_count, "status": "dispatched"},
            success=True,
        )
