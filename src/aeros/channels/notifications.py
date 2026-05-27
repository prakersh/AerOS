"""Unified notification fan-out across channels (in-app, email, Telegram)."""

import json

import structlog
from sqlmodel import Session, select

from aeros.models.user import User
from aeros.models.vendor import Vendor

logger = structlog.get_logger()


async def notify_vendor(
    session: Session,
    vendor: Vendor,
    *,
    event_type: str,
    subject: str,
    body: str,
    portal_url: str = "",
    thread_id: int | None = None,
    rfx_title: str = "",
) -> dict[str, bool]:
    """Fan out a notification to a vendor across their preferred channels.

    Args:
        session: Active database session.
        vendor: Target vendor record.
        event_type: Event type (e.g. rfq, reminder, po).
        subject: Notification subject line.
        body: Notification body text.
        portal_url: Optional portal link.
        thread_id: Optional thread ID for in-app delivery.
        rfx_title: Optional RFx title for email channel.

    Returns:
        Dict mapping channel name to delivery success boolean.
    """
    results: dict[str, bool] = {}

    prefs = {"email": True, "telegram": False, "in_app": True}
    if vendor.vendor_user_id:
        user = session.get(User, vendor.vendor_user_id)
        if user and user.notification_prefs_json:
            try:
                prefs = json.loads(user.notification_prefs_json)
            except json.JSONDecodeError:
                pass

    if prefs.get("in_app") and thread_id:
        from aeros.channels.in_app import deliver_in_app

        try:
            await deliver_in_app(session, thread_id, body, sender_kind="system")
            results["in_app"] = True
        except Exception as e:
            logger.error("notify.in_app.failed", error=str(e))
            results["in_app"] = False

    if prefs.get("email") and vendor.primary_email:
        from aeros.channels.email_out import send_rfx_invitation

        try:
            ok = await send_rfx_invitation(
                to_email=vendor.primary_email,
                vendor_name=vendor.name,
                rfx_title=rfx_title or subject,
                rfx_summary=body,
                correlation_token="",
                portal_url=portal_url,
            )
            results["email"] = ok
        except Exception as e:
            logger.error("notify.email.failed", error=str(e))
            results["email"] = False

    if prefs.get("telegram") and vendor.telegram_chat_id:
        from aeros.channels.telegram_bot import send_message

        try:
            r = await send_message(
                vendor.telegram_chat_id,
                f"<b>{subject}</b>\n\n{body}",
            )
            results["telegram"] = r is not None
        except Exception as e:
            logger.error("notify.telegram.failed", error=str(e))
            results["telegram"] = False

    return results
