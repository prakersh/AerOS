import json
import os
import hashlib
import re
import traceback
from datetime import datetime, timezone

import structlog
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from pydantic import BaseModel
from sqlmodel import Session, select

from aeros.db import get_session
from aeros.config import settings
from aeros.models.user import Role
from aeros.models.rfx import Attachment, ExtractionStatus, Message, Thread, RFxVendor, RFxVendorStatus
from aeros.models.vendor import Vendor
from aeros.security.auth_context import AuthContext, require_role
from aeros.services import rfx_service, offer_service

logger = structlog.get_logger()

router = APIRouter(prefix="/api/vendor", tags=["vendor"])


@router.get("/inbox")
def vendor_inbox(
    session: Session = Depends(get_session),
    caller: AuthContext = require_role(Role.VENDOR),
):
    vendor = session.exec(
        select(Vendor).where(Vendor.vendor_user_id == caller.user_id)
    ).first()
    if not vendor:
        return []
    return rfx_service.list_rfx_for_vendor(session, vendor.id)  # type: ignore[arg-type]


@router.get("/rfx/{rfx_id}/thread")
def get_thread(
    rfx_id: int,
    session: Session = Depends(get_session),
    caller: AuthContext = require_role(Role.VENDOR),
):
    vendor = session.exec(
        select(Vendor).where(Vendor.vendor_user_id == caller.user_id)
    ).first()
    if not vendor:
        raise HTTPException(403, "No vendor profile")
    thread = session.exec(
        select(Thread).where(Thread.rfx_id == rfx_id, Thread.vendor_id == vendor.id)
    ).first()
    if not thread:
        raise HTTPException(404, "Thread not found")
    messages = list(
        session.exec(
            select(Message).where(Message.thread_id == thread.id).order_by(Message.created_at)
        ).all()
    )
    return [
        {
            "id": m.id,
            "body_text": m.body_text,
            "sender_kind": m.sender_kind,
            "channel": m.channel,
            "created_at": m.created_at.isoformat() if m.created_at else "",
        }
        for m in messages
    ]


class ReplyRequest(BaseModel):
    body_text: str


@router.post("/rfx/{rfx_id}/reply")
def reply_to_rfx(
    rfx_id: int,
    body: ReplyRequest,
    session: Session = Depends(get_session),
    caller: AuthContext = require_role(Role.VENDOR),
):
    vendor = session.exec(
        select(Vendor).where(Vendor.vendor_user_id == caller.user_id)
    ).first()
    if not vendor:
        raise HTTPException(403, "No vendor profile")
    thread = session.exec(
        select(Thread).where(Thread.rfx_id == rfx_id, Thread.vendor_id == vendor.id)
    ).first()
    if not thread:
        raise HTTPException(404, "Thread not found")

    msg = Message(
        thread_id=thread.id,  # type: ignore[arg-type]
        sender_user_id=caller.user_id,
        sender_kind="vendor",
        channel="in_app",
        body_text=body.body_text,
    )
    session.add(msg)
    session.commit()
    session.refresh(msg)
    return msg


@router.post("/rfx/{rfx_id}/upload")
async def upload_file(
    rfx_id: int,
    file: UploadFile = File(...),
    session: Session = Depends(get_session),
    caller: AuthContext = require_role(Role.VENDOR),
):
    vendor = session.exec(
        select(Vendor).where(Vendor.vendor_user_id == caller.user_id)
    ).first()
    if not vendor:
        raise HTTPException(403, "No vendor profile")
    thread = session.exec(
        select(Thread).where(Thread.rfx_id == rfx_id, Thread.vendor_id == vendor.id)
    ).first()
    if not thread:
        raise HTTPException(404, "Thread not found")

    content = file.file.read()
    if len(content) > settings.max_upload_size_mb * 1024 * 1024:
        raise HTTPException(413, "File too large")

    sha = hashlib.sha256(content).hexdigest()
    upload_dir = os.path.join(settings.upload_dir, str(rfx_id), str(vendor.id))
    os.makedirs(upload_dir, exist_ok=True)
    raw_name = os.path.basename(file.filename or "upload")
    filename = re.sub(r"[^\w.\-]", "_", raw_name)[:255]
    storage_path = os.path.join(upload_dir, f"{sha[:8]}_{filename}")
    with open(storage_path, "wb") as f:
        f.write(content)

    msg = Message(
        thread_id=thread.id,  # type: ignore[arg-type]
        sender_user_id=caller.user_id,
        sender_kind="vendor",
        channel="in_app",
        body_text=f"Uploaded: {filename}",
    )
    session.add(msg)
    session.commit()
    session.refresh(msg)

    attachment = Attachment(
        message_id=msg.id,  # type: ignore[arg-type]
        filename=filename,
        mime_type=file.content_type or "application/octet-stream",
        storage_path=storage_path,
        size_bytes=len(content),
        sha256=sha,
        extraction_status=ExtractionStatus.PENDING,
    )
    session.add(attachment)
    session.commit()
    session.refresh(attachment)

    # Trigger extraction inline (background worker later)
    try:
        from aeros.agents.evaluation import EvaluationAgent
        from aeros.agents.base import AgentContext
        from aeros.ai.factory import get_chat_provider, get_vision_provider

        agent = EvaluationAgent()
        ctx = AgentContext(
            session=session,
            caller=caller,
            chat_provider=get_chat_provider(),
            vision_provider=get_vision_provider(),
        )
        result = await agent.run(ctx, str(msg.id))
        if result.success and result.data:
            offer_service.create_offer_from_extraction(
                session=session,
                rfx_id=rfx_id,
                vendor_id=vendor.id,  # type: ignore[arg-type]
                extraction_data=result.data,
                source_message_ids=[msg.id],  # type: ignore[list-item]
            )
            # Update vendor lane status to quoted
            rv = session.exec(
                select(RFxVendor).where(
                    RFxVendor.rfx_id == rfx_id,
                    RFxVendor.vendor_id == vendor.id,
                )
            ).first()
            if rv:
                rv.status = RFxVendorStatus.QUOTED
                session.add(rv)
                session.commit()
            logger.info("extraction.success", rfx_id=rfx_id, vendor_id=vendor.id)
    except Exception as e:
        logger.error("extraction.failed", error=str(e), traceback=traceback.format_exc())

    return {"message_id": msg.id, "attachment_id": attachment.id, "filename": filename}


@router.get("/rfx/{rfx_id}/uploads")
def list_uploads(
    rfx_id: int,
    session: Session = Depends(get_session),
    caller: AuthContext = require_role(Role.VENDOR),
):
    vendor = session.exec(
        select(Vendor).where(Vendor.vendor_user_id == caller.user_id)
    ).first()
    if not vendor:
        return []
    thread = session.exec(
        select(Thread).where(Thread.rfx_id == rfx_id, Thread.vendor_id == vendor.id)
    ).first()
    if not thread:
        return []
    messages = list(
        session.exec(select(Message).where(Message.thread_id == thread.id)).all()
    )
    msg_ids = [m.id for m in messages]
    if not msg_ids:
        return []
    attachments = list(
        session.exec(select(Attachment).where(Attachment.message_id.in_(msg_ids))).all()  # type: ignore[union-attr]
    )
    return [
        {
            "id": a.id,
            "filename": a.filename,
            "size_bytes": a.size_bytes,
            "extraction_status": a.extraction_status.value,
        }
        for a in attachments
    ]


class DeclineRequest(BaseModel):
    reason: str


@router.post("/rfx/{rfx_id}/decline")
def decline_rfx(
    rfx_id: int,
    body: DeclineRequest,
    session: Session = Depends(get_session),
    caller: AuthContext = require_role(Role.VENDOR),
):
    vendor = session.exec(
        select(Vendor).where(Vendor.vendor_user_id == caller.user_id)
    ).first()
    if not vendor:
        raise HTTPException(403, "No vendor profile")
    try:
        return rfx_service.decline_rfx_vendor(session, rfx_id, vendor.id, body.reason)  # type: ignore[arg-type]
    except ValueError as e:
        raise HTTPException(404, str(e))
