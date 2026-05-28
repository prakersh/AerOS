import json
import os
import re
from typing import Any

import structlog
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel
from sqlmodel import Session, select

from aeros.config import settings
from aeros.db import get_session
from aeros.models.offer import Offer
from aeros.models.rfx import (
    Attachment,
    ExtractionStatus,
    Message,
    RFxVendor,
    RFxVendorStatus,
    Thread,
)
from aeros.models.user import Role
from aeros.models.vendor import Vendor
from aeros.security.auth_context import AuthContext, require_role
from aeros.services import offer_service, rfx_service

logger = structlog.get_logger()

router = APIRouter(prefix="/api/vendor", tags=["vendor"])


@router.get("/inbox")
def vendor_inbox(
    session: Session = Depends(get_session),
    caller: AuthContext = require_role(Role.VENDOR),
) -> list[dict[str, Any]]:
    vendor = session.exec(select(Vendor).where(Vendor.vendor_user_id == caller.user_id)).first()
    if not vendor:
        return []
    return rfx_service.list_rfx_for_vendor(session, vendor.id)  # type: ignore[arg-type]


@router.get("/rfx/{rfx_id}/thread")
def get_thread(
    rfx_id: int,
    session: Session = Depends(get_session),
    caller: AuthContext = require_role(Role.VENDOR),
) -> dict[str, Any]:
    vendor = session.exec(select(Vendor).where(Vendor.vendor_user_id == caller.user_id)).first()
    if not vendor:
        raise HTTPException(403, "No vendor profile")
    thread = session.exec(
        select(Thread).where(Thread.rfx_id == rfx_id, Thread.vendor_id == vendor.id)
    ).first()
    if not thread:
        raise HTTPException(404, "Thread not found")

    from aeros.models.rfx import RFxLineItem, RFxRun
    from aeros.models.sku import SKU

    rfx = session.get(RFxRun, rfx_id)

    messages = list(
        session.exec(
            select(Message).where(Message.thread_id == thread.id).order_by(Message.created_at)  # type: ignore[arg-type]
        ).all()
    )

    line_items_raw = list(
        session.exec(select(RFxLineItem).where(RFxLineItem.rfx_id == rfx_id)).all()
    )
    line_items = []
    for li in line_items_raw:
        sku = session.get(SKU, li.sku_id)
        line_items.append(
            {
                "id": li.id,
                "sku": sku.code if sku else "",
                "description": sku.name if sku else "",
                "quantity": li.qty,
                "unit": li.unit_override or (sku.unit if sku else ""),
                "target_price": li.target_price,
            }
        )

    attachments = (
        list(
            session.exec(
                select(Attachment).where(
                    Attachment.message_id.in_(  # type: ignore[attr-defined]
                        [m.id for m in messages]
                    )
                )
            ).all()
        )
        if messages
        else []
    )

    # Mark vendor lane as VIEWED on first thread access
    rv = session.exec(
        select(RFxVendor).where(
            RFxVendor.rfx_id == rfx_id,
            RFxVendor.vendor_id == vendor.id,
        )
    ).first()
    if rv and rv.status == RFxVendorStatus.INVITED:
        rv.status = RFxVendorStatus.VIEWED
        session.add(rv)
        session.commit()

    # Load existing offer for this vendor (latest non-superseded)
    existing_offer = session.exec(
        select(Offer).where(
            Offer.rfx_id == rfx_id,
            Offer.vendor_id == vendor.id,
            Offer.superseded_by_offer_id == None,  # noqa: E711
        )
    ).first()

    existing_quote: dict[str, Any] | None = None
    if existing_offer:
        offer_line_items = json.loads(existing_offer.line_items_json or "[]")
        existing_quote = {
            "offer_id": existing_offer.id,
            "revision_no": existing_offer.revision_no,
            "line_items": offer_line_items,
            "total_quote": existing_offer.total_quote,
            "payment_terms": existing_offer.payment_terms,
            "delivery_terms": existing_offer.delivery_terms,
            "validity_until": (
                existing_offer.validity_until.isoformat() if existing_offer.validity_until else None
            ),
            "vendor_remarks": existing_offer.vendor_remarks,
        }

    vendor_lane_status = rv.status.value if rv else "invited"

    return {
        "rfx_id": str(rfx_id),
        "rfx_title": rfx.title if rfx else "",
        "rfx_status": rfx.status.value
        if rfx and hasattr(rfx.status, "value")
        else str(rfx.status)
        if rfx
        else "",
        "vendor_status": vendor_lane_status,
        "deadline": rfx.response_deadline.isoformat() if rfx and rfx.response_deadline else None,
        "currency": rfx.currency_for_this_rfx if rfx else "INR",
        "payment_terms": rfx.payment_terms_for_this_rfx if rfx else None,
        "delivery_terms": rfx.delivery_terms_for_this_rfx if rfx else None,
        "tax_terms": rfx.tax_treatment_for_this_rfx if rfx else None,
        "line_items": line_items,
        "existing_quote": existing_quote,
        "messages": [
            {
                "id": m.id,
                "body_text": m.body_text,
                "sender_kind": m.sender_kind,
                "channel": m.channel,
                "created_at": m.created_at.isoformat() if m.created_at else "",
            }
            for m in messages
        ],
        "attachments": [
            {
                "id": a.id,
                "filename": a.filename,
                "size_bytes": a.size_bytes,
                "extraction_status": a.extraction_status.value
                if hasattr(a.extraction_status, "value")
                else str(a.extraction_status),
            }
            for a in attachments
        ],
    }


class ReplyRequest(BaseModel):
    body_text: str


@router.post("/rfx/{rfx_id}/reply")
def reply_to_rfx(
    rfx_id: int,
    body: ReplyRequest,
    session: Session = Depends(get_session),
    caller: AuthContext = require_role(Role.VENDOR),
) -> Any:
    vendor = session.exec(select(Vendor).where(Vendor.vendor_user_id == caller.user_id)).first()
    if not vendor:
        raise HTTPException(403, "No vendor profile")
    thread = session.exec(
        select(Thread).where(Thread.rfx_id == rfx_id, Thread.vendor_id == vendor.id)
    ).first()
    if not thread:
        raise HTTPException(404, "Thread not found")

    msg = Message(
        thread_id=thread.id,
        sender_user_id=caller.user_id,
        sender_kind="vendor",
        channel="in_app",
        body_text=body.body_text,
    )
    session.add(msg)
    session.flush()
    session.commit()
    session.refresh(msg)
    return msg


@router.post("/rfx/{rfx_id}/upload")
async def upload_file(
    rfx_id: int,
    file: UploadFile = File(...),
    session: Session = Depends(get_session),
    caller: AuthContext = require_role(Role.VENDOR),
) -> dict[str, Any]:
    vendor = session.exec(select(Vendor).where(Vendor.vendor_user_id == caller.user_id)).first()
    if not vendor:
        raise HTTPException(403, "No vendor profile")
    thread = session.exec(
        select(Thread).where(Thread.rfx_id == rfx_id, Thread.vendor_id == vendor.id)
    ).first()
    if not thread:
        raise HTTPException(404, "Thread not found")

    content = await file.read()
    raw_name = os.path.basename(file.filename or "upload")
    filename = re.sub(r"[^\w.\-]", "_", raw_name)[:255]

    from aeros.services.file_service import validate_file

    validation = validate_file(content, filename)
    if not validation.is_valid:
        raise HTTPException(422, validation.error)

    sha = validation.sha256
    upload_dir = os.path.join(settings.upload_dir, str(rfx_id), str(vendor.id))
    os.makedirs(upload_dir, exist_ok=True)
    storage_path = os.path.join(upload_dir, f"{sha[:8]}_{filename}")
    with open(storage_path, "wb") as f:
        f.write(content)

    msg = Message(
        thread_id=thread.id,
        sender_user_id=caller.user_id,
        sender_kind="vendor",
        channel="in_app",
        body_text=f"Uploaded: {filename}",
    )
    session.add(msg)
    session.flush()
    session.commit()
    session.refresh(msg)

    attachment = Attachment(
        message_id=msg.id,
        filename=filename,
        mime_type=file.content_type or "application/octet-stream",
        storage_path=storage_path,
        size_bytes=len(content),
        sha256=sha,
        extraction_status=ExtractionStatus.PENDING,
    )
    session.add(attachment)
    session.flush()
    session.commit()
    session.refresh(attachment)

    # Extract synchronously so the vendor gets immediate feedback. The worker
    # helper owns the status transitions (EXTRACTED / FAILED) and flips the lane
    # to QUOTED on success, so a failed extraction no longer reports success.
    from aeros.workers.extract_offer import extract_offer_from_attachment

    assert attachment.id is not None and msg.id is not None and vendor.id is not None
    extracted = await extract_offer_from_attachment(
        attachment.id, rfx_id, vendor.id, msg.id, session=session
    )

    return {
        "message_id": msg.id,
        "attachment_id": attachment.id,
        "filename": filename,
        "extraction_status": "extracted" if extracted else "failed",
    }


class CopilotRequest(BaseModel):
    message: str
    history: list[dict[str, str]] = []


@router.post("/rfx/{rfx_id}/copilot")
async def vendor_copilot(
    rfx_id: int,
    body: CopilotRequest,
    session: Session = Depends(get_session),
    caller: AuthContext = require_role(Role.VENDOR),
) -> dict[str, Any]:
    """Vendor co-pilot: real LLM guidance for composing an RFQ response."""
    from aeros.agents.base import AgentContext
    from aeros.agents.vendor_copilot import VendorCopilotAgent
    from aeros.ai.factory import get_chat_provider
    from aeros.models.rfx import RFxLineItem, RFxRun
    from aeros.models.sku import SKU

    vendor = session.exec(select(Vendor).where(Vendor.vendor_user_id == caller.user_id)).first()
    if not vendor:
        raise HTTPException(403, "No vendor profile")
    rv = session.exec(
        select(RFxVendor).where(RFxVendor.rfx_id == rfx_id, RFxVendor.vendor_id == vendor.id)
    ).first()
    if not rv:
        raise HTTPException(403, "Not invited to this RFx")

    rfx = session.get(RFxRun, rfx_id)
    if not rfx:
        raise HTTPException(404, "RFx not found")

    line_items = session.exec(select(RFxLineItem).where(RFxLineItem.rfx_id == rfx_id)).all()
    item_lines = []
    for li in line_items:
        sku = session.get(SKU, li.sku_id)
        unit = li.unit_override or (sku.unit if sku else "")
        item_lines.append(f"- {sku.name if sku else 'item'}: qty {li.qty} {unit}".rstrip())
    rfx_context = (
        f"Title: {rfx.title}\n"
        f"Payment terms: {rfx.payment_terms_for_this_rfx}\n"
        f"Delivery terms: {rfx.delivery_terms_for_this_rfx}\n"
        f"Currency: {rfx.currency_for_this_rfx}\n"
        f"Notes: {rfx.notes_for_vendors or '—'}\n"
        "Requested items:\n" + ("\n".join(item_lines) or "—")
    )

    chat_provider = get_chat_provider()
    chat_provider.user_id = caller.user_id
    agent = VendorCopilotAgent()
    ctx = AgentContext(
        session=session,
        caller=caller,
        chat_provider=chat_provider,
        metadata={"history": body.history, "rfx_context": rfx_context},
    )
    result = await agent.run(ctx, body.message)
    return result.data or {"message": result.message, "status": "chatting"}


@router.get("/rfx/{rfx_id}/uploads")
def list_uploads(
    rfx_id: int,
    session: Session = Depends(get_session),
    caller: AuthContext = require_role(Role.VENDOR),
) -> list[dict[str, Any]]:
    vendor = session.exec(select(Vendor).where(Vendor.vendor_user_id == caller.user_id)).first()
    if not vendor:
        return []
    thread = session.exec(
        select(Thread).where(Thread.rfx_id == rfx_id, Thread.vendor_id == vendor.id)
    ).first()
    if not thread:
        return []
    messages = list(session.exec(select(Message).where(Message.thread_id == thread.id)).all())
    msg_ids = [m.id for m in messages]
    if not msg_ids:
        return []
    attachments = list(
        session.exec(select(Attachment).where(Attachment.message_id.in_(msg_ids))).all()  # type: ignore[attr-defined]
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


class QuoteLineItem(BaseModel):
    line_item_id: int
    unit_price: float
    lead_time_days: int | None = None
    notes: str | None = None


class SubmitQuoteRequest(BaseModel):
    line_items: list[QuoteLineItem]
    payment_terms: str | None = None
    delivery_terms: str | None = None
    validity_until: str | None = None
    vendor_remarks: str | None = None


@router.post("/rfx/{rfx_id}/submit-quote")
def submit_quote(
    rfx_id: int,
    body: SubmitQuoteRequest,
    session: Session = Depends(get_session),
    caller: AuthContext = require_role(Role.VENDOR),
) -> dict[str, Any]:
    vendor = session.exec(select(Vendor).where(Vendor.vendor_user_id == caller.user_id)).first()
    if not vendor:
        raise HTTPException(403, "No vendor profile")
    thread = session.exec(
        select(Thread).where(Thread.rfx_id == rfx_id, Thread.vendor_id == vendor.id)
    ).first()
    if not thread:
        raise HTTPException(404, "Thread not found")

    # Look up quantities from RFxLineItem for accurate total
    from aeros.models.rfx import RFxLineItem

    line_item_qty_map = {}
    for li in body.line_items:
        if li.line_item_id not in line_item_qty_map:
            rfx_li = session.get(RFxLineItem, li.line_item_id)
            line_item_qty_map[li.line_item_id] = rfx_li.qty if rfx_li else 0
    total = sum(li.unit_price * line_item_qty_map.get(li.line_item_id, 0) for li in body.line_items)

    extraction_data = {
        "line_items": [
            {
                "line_item_id": li.line_item_id,
                "unit_price": li.unit_price,
                "lead_time_days": li.lead_time_days,
                "notes": li.notes,
                "confidence": 1.0,
            }
            for li in body.line_items
        ],
        "total_quote": total,
        "payment_terms": body.payment_terms,
        "delivery_terms": body.delivery_terms,
        "vendor_remarks": body.vendor_remarks,
        "confidence_overall": 1.0,
    }

    # Record the quote as a message in the thread
    items_text = ", ".join(
        f"Item #{li.line_item_id}: {li.unit_price}/unit" for li in body.line_items
    )
    msg = Message(
        thread_id=thread.id,
        sender_user_id=caller.user_id,
        sender_kind="vendor",
        channel="in_app",
        body_text=f"Structured quote submitted: {items_text}",
    )
    session.add(msg)
    session.flush()
    session.commit()
    session.refresh(msg)

    offer = offer_service.create_offer_from_extraction(
        session=session,
        rfx_id=rfx_id,
        vendor_id=vendor.id,  # type: ignore[arg-type]
        extraction_data=extraction_data,
        source_message_ids=[msg.id],  # type: ignore[list-item]
    )

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

    return {
        "offer_id": offer.id,
        "revision_no": offer.revision_no,
        "message": "Quote submitted successfully",
    }


class DeclineRequest(BaseModel):
    reason: str = ""
    category: str = "other"


@router.post("/rfx/{rfx_id}/decline")
def decline_rfx(
    rfx_id: int,
    body: DeclineRequest,
    session: Session = Depends(get_session),
    caller: AuthContext = require_role(Role.VENDOR),
) -> Any:
    vendor = session.exec(select(Vendor).where(Vendor.vendor_user_id == caller.user_id)).first()
    if not vendor:
        raise HTTPException(403, "No vendor profile")
    try:
        return rfx_service.decline_rfx_vendor(session, rfx_id, vendor.id, body.reason)  # type: ignore[arg-type]
    except ValueError as e:
        raise HTTPException(404, str(e)) from None


class UpdateVendorProfileRequest(BaseModel):
    vendor_name: str | None = None
    phone: str | None = None


@router.put("/profile")
def update_vendor_profile(
    body: UpdateVendorProfileRequest,
    session: Session = Depends(get_session),
    caller: AuthContext = require_role(Role.VENDOR),
) -> dict[str, Any]:
    vendor = session.exec(select(Vendor).where(Vendor.vendor_user_id == caller.user_id)).first()
    if not vendor:
        raise HTTPException(403, "No vendor profile")
    if body.vendor_name is not None:
        vendor.name = body.vendor_name
        from aeros.models.user import User

        user = session.get(User, caller.user_id)
        if user:
            user.display_name = body.vendor_name
            session.add(user)
    if body.phone is not None:
        vendor.phone = body.phone
    session.add(vendor)
    session.commit()
    session.refresh(vendor)
    return {
        "vendor_name": vendor.name,
        "email": vendor.primary_email,
        "phone": vendor.phone or "",
    }
