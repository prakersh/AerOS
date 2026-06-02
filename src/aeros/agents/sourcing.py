"""SourcingAgent — composes RFx messages, proposes dispatch plan,
dispatches on confirmation."""

import json
from typing import Any

import structlog
from sqlmodel import select

from aeros.agents.base import AgentContext, AgentResult, BaseAgent, parse_llm_json
from aeros.ai.base import ChatMessage
from aeros.channels.correlation import generate_correlation_token
from aeros.channels.email_out import send_rfx_invitation
from aeros.config import settings
from aeros.models.rfx import Message, RFxLineItem, RFxRun, RFxVendor, Thread
from aeros.models.vendor import Vendor
from aeros.services import rfx_service

logger = structlog.get_logger()

SOURCING_SYSTEM_PROMPT = (
    "You are the AEROS Sourcing Agent. Your job is to compose "
    "clear, professional vendor invitation messages for RFQs.\n\n"
    "Given the RFx details and line items, compose a concise "
    "summary that vendors can understand and quote against.\n\n"
    "OUTPUT (JSON):\n"
    "{\n"
    '  "subject": "Short subject line",\n'
    '  "summary": "Multi-line summary of what\'s needed, '
    'including items, quantities, delivery window, and terms",\n'
    '  "per_vendor_notes": {} // optional per-vendor customization\n'
    "}\n"
)


class SourcingAgent(BaseAgent):
    name = "sourcing"

    async def run(self, ctx: AgentContext, user_input: str) -> AgentResult:
        action = json.loads(user_input) if user_input.startswith("{") else {"action": user_input}
        rfx_id = action.get("rfx_id") or ctx.rfx_id

        if not rfx_id:
            return AgentResult(message="I couldn't tell which request this is for.", success=False)

        rfx = ctx.session.get(RFxRun, rfx_id)
        if not rfx:
            return AgentResult(message="I couldn't find that request.", success=False)

        line_items = list(
            ctx.session.exec(select(RFxLineItem).where(RFxLineItem.rfx_id == rfx_id)).all()
        )

        if action.get("action") == "propose_dispatch":
            vendor_ids: list[int] = action.get("vendor_ids", [])  # type: ignore[assignment]
            return await self._propose_dispatch(ctx, rfx, line_items, vendor_ids)
        elif action.get("action") == "confirm_dispatch":
            dispatch_plan: list[Any] = action.get("dispatch_plan", [])  # type: ignore[assignment]
            return await self._confirm_dispatch(
                ctx,
                rfx,
                line_items,
                dispatch_plan,
            )

        return AgentResult(message="Unknown action", success=False)

    async def _propose_dispatch(
        self, ctx: AgentContext, rfx: RFxRun, line_items: list[Any], vendor_ids: list[int]
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

            dispatch_plan.append(
                {
                    "vendor_id": vendor.id,
                    "vendor_name": vendor.name,
                    "channel": channel,
                    "channel_detail": detail,
                }
            )

        return AgentResult(
            message="Here's the plan for reaching each vendor. Confirm to send.",
            data={
                "dispatch_plan": dispatch_plan,
                "status": "confirming_dispatch",
            },
            success=True,
        )

    def _get_items_for_vendor(
        self, ctx: AgentContext, rfx_id: int, vendor_id: int, all_line_items: list[Any]
    ) -> list[Any]:
        """Return the line items assigned to this vendor, or all items if none assigned."""
        rv = ctx.session.exec(
            select(RFxVendor).where(RFxVendor.rfx_id == rfx_id, RFxVendor.vendor_id == vendor_id)
        ).first()
        if rv and rv.line_item_ids_json:
            try:
                assigned_ids = set(json.loads(rv.line_item_ids_json))
                return [li for li in all_line_items if li.id in assigned_ids]
            except (json.JSONDecodeError, TypeError):
                pass
        return all_line_items

    async def _confirm_dispatch(
        self, ctx: AgentContext, rfx: RFxRun, line_items: list[Any], dispatch_plan: list[Any]
    ) -> AgentResult:
        # Compose the RFx summary via LLM using all items for the base summary
        items_text = "\n".join(
            f"- {li.qty} {li.unit_override or ''} (SKU ID: {li.sku_id})" for li in line_items
        )
        messages = [
            ChatMessage(role="system", content=SOURCING_SYSTEM_PROMPT),
            ChatMessage(
                role="user",
                content=f"""Compose an RFQ invitation for:
Title: {rfx.title}
Items:
{items_text}
Delivery: {rfx.delivery_window_start} to {rfx.delivery_window_end}
Deadline: {rfx.response_deadline}
Terms: {rfx.payment_terms_for_this_rfx}, {rfx.delivery_terms_for_this_rfx}
Currency: {rfx.currency_for_this_rfx}
""",
            ),
        ]
        resp = await ctx.chat_provider.chat(
            messages,
            temperature=0.3,
            max_tokens=16384,
            response_format={"type": "json_object"},
        )
        composed = parse_llm_json(resp.content, {"subject": rfx.title, "summary": resp.content})

        base_summary = composed.get("summary", rfx.title)
        dispatched_count = 0
        delivery_errors: list[str] = []

        for entry in dispatch_plan:
            vendor_id = entry["vendor_id"]
            channel = entry["channel"]
            vendor = ctx.session.get(Vendor, vendor_id)
            if not vendor:
                continue

            # Determine which items this vendor should receive
            assert rfx.id is not None
            vendor_items = self._get_items_for_vendor(ctx, rfx.id, vendor_id, line_items)
            if not vendor_items:
                continue

            # Build vendor-specific summary with only assigned items
            vendor_items_text = "\n".join(
                f"- {li.qty} {li.unit_override or ''} (SKU ID: {li.sku_id})" for li in vendor_items
            )
            summary = f"{base_summary}\n\nItems for your quote:\n{vendor_items_text}"

            # Generate correlation token
            token, token_hash = generate_correlation_token(rfx.id, vendor_id)

            # Create RFxVendor + Thread
            rfx_service.invite_vendor(ctx.session, rfx.id, vendor_id, token_hash)

            portal_url = f"{settings.frontend_url}/vendor/rfx/{rfx.id}"

            # Dispatch based on channel. Isolate each send: a single failed
            # email/telegram must not abort the loop and leave the RFx stuck in
            # DRAFTING with some vendors already invited. The vendor is invited
            # regardless (above) and can always use the portal link.
            try:
                if channel == "email" and vendor.primary_email:
                    await send_rfx_invitation(
                        to_email=vendor.primary_email,
                        vendor_name=vendor.name,
                        rfx_title=rfx.title,
                        rfx_summary=summary,
                        correlation_token=token,
                        portal_url=portal_url,
                    )
                elif channel == "telegram" and vendor.telegram_chat_id:
                    from aeros.channels.telegram_bot import send_rfx_invitation as tg_send

                    await tg_send(
                        chat_id=vendor.telegram_chat_id,
                        vendor_name=vendor.name,
                        rfx_title=rfx.title,
                        rfx_summary=summary,
                        portal_url=portal_url,
                    )
            except Exception as e:
                logger.error(
                    "sourcing.dispatch.channel_failed",
                    vendor_id=vendor_id,
                    channel=channel,
                    error=str(e),
                )
                delivery_errors.append(vendor.name)
            # in_app: create a system message in the thread
            thread = ctx.session.exec(
                select(Thread).where(Thread.rfx_id == rfx.id, Thread.vendor_id == vendor_id)
            ).first()
            if thread:
                sys_msg = Message(
                    thread_id=thread.id,
                    sender_kind="system",
                    channel="system",
                    body_text=f"RFQ Invitation: {rfx.title}\n\n{summary}",
                )
                ctx.session.add(sys_msg)

            dispatched_count += 1

        # Update RFx status — always runs now that per-vendor sends are isolated.
        rfx_service.dispatch_rfx(ctx.session, rfx.id, ctx.caller.user_id)  # type: ignore[arg-type]
        ctx.session.commit()

        vendor_word = "vendor" if dispatched_count == 1 else "vendors"
        message = f"Sent to {dispatched_count} {vendor_word}."
        if delivery_errors:
            failed = ", ".join(delivery_errors)
            message += (
                f" We couldn't reach {failed} directly, but they can still respond from the portal."
            )

        return AgentResult(
            message=message,
            data={
                "dispatched_count": dispatched_count,
                "status": "dispatched",
                "delivery_errors": delivery_errors,
            },
            success=True,
        )
