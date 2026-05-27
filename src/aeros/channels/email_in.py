"""Inbound email processing — IMAP poll + parse for vendor replies."""

import asyncio
import email
import hashlib
import os
import re
from email.message import EmailMessage
from typing import Any

import structlog

from aeros.config import settings

logger = structlog.get_logger()


def extract_correlation_token(email_address: str) -> str | None:
    """Extract the correlation token from a procurement reply-to address.

    Args:
        email_address: Email address like ``procurement+TOKEN@domain``.

    Returns:
        The token string, or None if the address does not match.
    """
    match = re.match(r"procurement\+([^@]+)@", email_address)
    return match.group(1) if match else None


def parse_email_message(raw_bytes: bytes) -> dict[str, Any]:
    """Parse raw RFC822 bytes into a structured dict.

    Args:
        raw_bytes: Raw email bytes.

    Returns:
        Dict with keys: from, to, subject, in_reply_to, message_id,
        body_text, body_html, attachments.
    """
    msg = email.message_from_bytes(raw_bytes)
    result: dict[str, Any] = {
        "from": msg.get("From", ""),
        "to": msg.get("To", ""),
        "subject": msg.get("Subject", ""),
        "in_reply_to": msg.get("In-Reply-To", ""),
        "message_id": msg.get("Message-ID", ""),
        "body_text": "",
        "body_html": None,
        "attachments": [],
    }

    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            disposition = str(part.get("Content-Disposition", ""))

            if "attachment" in disposition:
                payload = part.get_payload(decode=True)
                if payload:
                    result["attachments"].append({
                        "filename": part.get_filename() or "attachment",
                        "mime_type": content_type,
                        "data": payload,
                    })
            elif content_type == "text/plain" and not result["body_text"]:
                payload = part.get_payload(decode=True)
                if payload:
                    result["body_text"] = payload.decode("utf-8", errors="replace")
            elif content_type == "text/html" and not result["body_html"]:
                payload = part.get_payload(decode=True)
                if payload:
                    result["body_html"] = payload.decode("utf-8", errors="replace")
    else:
        payload = msg.get_payload(decode=True)
        if payload:
            if msg.get_content_type() == "text/html":
                result["body_html"] = payload.decode("utf-8", errors="replace")
            else:
                result["body_text"] = payload.decode("utf-8", errors="replace")

    return result


def save_attachments(
    attachments: list[dict],
    rfx_id: int,
    vendor_id: int,
) -> list[dict]:
    """Save attachment data to disk under the upload directory.

    Args:
        attachments: List of dicts with filename, mime_type, data keys.
        rfx_id: RFx ID for directory structure.
        vendor_id: Vendor ID for directory structure.

    Returns:
        List of dicts with filename, mime_type, storage_path, size_bytes, sha256.
    """
    saved: list[dict] = []
    upload_dir = os.path.join(settings.upload_dir, str(rfx_id), str(vendor_id))
    os.makedirs(upload_dir, exist_ok=True)

    for att in attachments:
        data = att["data"]
        sha = hashlib.sha256(data).hexdigest()
        filename = att["filename"]
        path = os.path.join(upload_dir, f"{sha[:8]}_{filename}")
        with open(path, "wb") as f:
            f.write(data)
        saved.append({
            "filename": filename,
            "mime_type": att["mime_type"],
            "storage_path": path,
            "size_bytes": len(data),
            "sha256": sha,
        })
    return saved


async def poll_imap_once() -> list[dict]:
    """Poll IMAP for new messages. Returns list of parsed emails.

    Uses imaplib to connect to the configured IMAP server and fetch
    all UNSEEN messages.

    Returns:
        List of parsed email dicts (see parse_email_message).
    """
    try:
        import imaplib

        mail = imaplib.IMAP4(settings.imap_host, settings.imap_port)
        if settings.imap_username:
            mail.login(settings.imap_username, settings.imap_password)
        mail.select("INBOX")
        _, message_ids = mail.search(None, "UNSEEN")

        results: list[dict] = []
        for msg_id in message_ids[0].split():
            if not msg_id:
                continue
            _, msg_data = mail.fetch(msg_id, "(RFC822)")
            if msg_data[0] is None:
                continue
            raw = msg_data[0][1]
            if isinstance(raw, bytes):
                parsed = parse_email_message(raw)
                results.append(parsed)

        mail.logout()
        return results
    except Exception as e:
        logger.error("imap.poll_failed", error=str(e))
        return []
