"""Telegram webhook endpoint + dev-only fake endpoint."""

import hashlib
import os
from typing import Any

import structlog
from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select

from aeros.channels import telegram_bot
from aeros.config import settings
from aeros.db import get_session
from aeros.models.rfx import (
    Attachment,
    ExtractionStatus,
    Message,
    Thread,
)
from aeros.models.vendor import Vendor

logger = structlog.get_logger()

router = APIRouter(tags=["telegram"])


class TelegramUpdate(BaseModel):
    """Subset of a Telegram Update object we care about."""

    update_id: int
    message: dict[str, Any] | None = None


@router.post("/api/webhook/telegram")
async def telegram_webhook(
    update: TelegramUpdate,
    session: Session = Depends(get_session),
    x_telegram_bot_api_secret_token: str | None = Header(None),
) -> dict[str, Any]:
    """Handle an incoming Telegram webhook update.

    Validates the secret token, links vendors via /start,
    and persists messages + attachments.
    """
    if settings.telegram_webhook_secret and not telegram_bot.verify_webhook_secret(
        x_telegram_bot_api_secret_token or ""
    ):
        raise HTTPException(403, "Invalid webhook secret")

    if not update.message:
        return {"ok": True}

    msg = update.message
    chat_id = str(msg.get("chat", {}).get("id", ""))
    text = msg.get("text", "")

    # Handle /start command — link vendor's Telegram account
    if text.startswith("/start "):
        token = text.split(" ", 1)[1].strip()
        logger.info("telegram.start", chat_id=chat_id, token=token[:8])
        vendor = session.exec(select(Vendor).where(Vendor.telegram_chat_id == token)).first()
        if vendor:
            vendor.telegram_chat_id = chat_id
            session.add(vendor)
            session.commit()
            await telegram_bot.send_message(
                chat_id,
                "Telegram linked successfully! You'll receive RFQ notifications here.",
            )
        return {"ok": True}

    # Look up vendor by chat_id
    vendor = session.exec(select(Vendor).where(Vendor.telegram_chat_id == chat_id)).first()
    if not vendor:
        await telegram_bot.send_message(
            chat_id,
            "Please use /start <token> to link your account first.",
        )
        return {"ok": True}

    # Find the most recent thread for this vendor
    thread = session.exec(
        select(Thread).where(Thread.vendor_id == vendor.id).order_by(Thread.created_at.desc())  # type: ignore[attr-defined]
    ).first()
    if not thread:
        await telegram_bot.send_message(chat_id, "No active RFQ thread found.")
        return {"ok": True}

    # Persist the message
    message = Message(
        thread_id=thread.id,
        sender_user_id=vendor.vendor_user_id,
        sender_kind="vendor",
        channel="telegram",
        body_text=text,
        raw_payload_json=str(msg),
    )
    session.add(message)
    session.commit()
    session.refresh(message)

    # Handle photo/document attachments
    document = msg.get("document")
    photo = msg.get("photo")
    file_id: str | None = None
    filename = "telegram_upload"
    mime_type = "application/octet-stream"

    if document:
        file_id = document.get("file_id")
        filename = document.get("file_name", "document")
        mime_type = document.get("mime_type", "application/octet-stream")
    elif photo:
        best = max(photo, key=lambda p: p.get("file_size", 0))
        file_id = best.get("file_id")
        filename = "photo.jpg"
        mime_type = "image/jpeg"

    if file_id:
        save_dir = os.path.join(settings.upload_dir, str(thread.rfx_id), str(vendor.id))
        local_path = await telegram_bot.download_file(file_id, save_dir)
        if local_path:
            size = os.path.getsize(local_path)
            with open(local_path, "rb") as f:
                sha = hashlib.sha256(f.read()).hexdigest()
            att = Attachment(
                message_id=message.id,
                filename=filename,
                mime_type=mime_type,
                storage_path=local_path,
                size_bytes=size,
                sha256=sha,
                extraction_status=ExtractionStatus.PENDING,
            )
            session.add(att)
            session.commit()
            logger.info(
                "telegram.attachment_saved",
                filename=filename,
                vendor_id=vendor.id,
            )

    return {"ok": True}


class FakeTelegramUpdate(BaseModel):
    """Request body for the dev-only fake Telegram endpoint."""

    chat_id: str
    text: str = ""
    document_path: str | None = None


@router.post("/api/test/telegram-fake")
async def fake_telegram_update(
    body: FakeTelegramUpdate,
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    """Dev-only endpoint to simulate a Telegram update without a real bot."""
    update = TelegramUpdate(
        update_id=0,
        message={
            "chat": {"id": body.chat_id},
            "text": body.text,
            "from": {"id": body.chat_id, "first_name": "Test"},
        },
    )
    return await telegram_webhook(update, session)
