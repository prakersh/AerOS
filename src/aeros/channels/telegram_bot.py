"""Telegram bot integration — send messages and download files."""

import hashlib
import hmac
import os

import httpx
import structlog

from aeros.config import settings

logger = structlog.get_logger()

TELEGRAM_API = "https://api.telegram.org"


def _bot_url(method: str) -> str:
    """Build a Telegram Bot API URL for the given method."""
    return f"{TELEGRAM_API}/bot{settings.telegram_bot_token}/{method}"


async def send_message(
    chat_id: str,
    text: str,
    parse_mode: str = "HTML",
) -> dict | None:
    """Send a text message to a Telegram chat.

    Args:
        chat_id: Telegram chat ID.
        text: Message text.
        parse_mode: Parse mode (HTML, Markdown, etc.).

    Returns:
        Telegram API response dict, or None on failure.
    """
    if not settings.telegram_bot_token:
        logger.warning("telegram.no_token", chat_id=chat_id)
        return None

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            _bot_url("sendMessage"),
            json={"chat_id": chat_id, "text": text, "parse_mode": parse_mode},
        )
        if resp.status_code == 200:
            return resp.json()
        logger.error("telegram.send_failed", status=resp.status_code, body=resp.text)
        return None


async def send_rfx_invitation(
    chat_id: str,
    vendor_name: str,
    rfx_title: str,
    rfx_summary: str,
    portal_url: str,
) -> bool:
    """Send an RFQ invitation to a vendor via Telegram.

    Args:
        chat_id: Telegram chat ID.
        vendor_name: Vendor display name.
        rfx_title: Title of the RFQ.
        rfx_summary: Summary text.
        portal_url: Link to the vendor portal.

    Returns:
        True if message was sent successfully.
    """
    text = (
        f"<b>New RFQ: {rfx_title}</b>\n\n"
        f"Hi {vendor_name},\n\n"
        f"You have received a new Request for Quotation:\n\n"
        f"<pre>{rfx_summary}</pre>\n\n"
        f"Please submit your quote:\n"
        f'<a href="{portal_url}">Open Portal</a>\n\n'
        f"Or reply with your price list (photo, PDF, etc.) directly here."
    )
    result = await send_message(chat_id, text)
    return result is not None


async def send_po_notification(
    chat_id: str,
    vendor_name: str,
    po_number: str,
    portal_url: str,
) -> bool:
    """Send a Purchase Order notification via Telegram.

    Args:
        chat_id: Telegram chat ID.
        vendor_name: Vendor display name.
        po_number: PO number string.
        portal_url: Link to download the PO.

    Returns:
        True if message was sent successfully.
    """
    text = (
        f"<b>Purchase Order: {po_number}</b>\n\n"
        f"Hi {vendor_name},\n\n"
        f"A purchase order has been issued to you.\n"
        f'<a href="{portal_url}">Download PO</a>'
    )
    result = await send_message(chat_id, text)
    return result is not None


def verify_webhook_secret(token: str) -> bool:
    """Verify a Telegram webhook secret token.

    Args:
        token: Token from X-Telegram-Bot-Api-Secret-Token header.

    Returns:
        True if the token matches or no secret is configured.
    """
    if not settings.telegram_webhook_secret:
        return True
    return hmac.compare_digest(token, settings.telegram_webhook_secret)


async def download_file(file_id: str, save_dir: str) -> str | None:
    """Download a file from Telegram and save it locally.

    Args:
        file_id: Telegram file_id.
        save_dir: Local directory to save the file.

    Returns:
        Local file path, or None on failure.
    """
    if not settings.telegram_bot_token:
        return None

    async with httpx.AsyncClient() as client:
        resp = await client.get(_bot_url("getFile"), params={"file_id": file_id})
        if resp.status_code != 200:
            return None
        file_path = resp.json().get("result", {}).get("file_path")
        if not file_path:
            return None

        file_url = f"{TELEGRAM_API}/file/bot{settings.telegram_bot_token}/{file_path}"
        file_resp = await client.get(file_url)
        if file_resp.status_code != 200:
            return None

        os.makedirs(save_dir, exist_ok=True)
        filename = os.path.basename(file_path)
        local_path = os.path.join(save_dir, filename)
        with open(local_path, "wb") as f:
            f.write(file_resp.content)
        return local_path
