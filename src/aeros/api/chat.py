"""Chat API — conversational AI for buyer + vendor co-pilots, plus RFx actions."""

import contextlib
import hashlib
import json
import os
import re
import traceback
from datetime import datetime
from typing import Any

import structlog
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlmodel import Session, select

from aeros.agents.base import AgentContext
from aeros.agents.sourcing import SourcingAgent
from aeros.ai.factory import get_chat_provider, get_vision_provider
from aeros.config import settings
from aeros.db import get_session
from aeros.models.sku import SKU
from aeros.models.user import Role
from aeros.security.auth_context import AuthContext, get_current_user
from aeros.services import rfx_service

logger = structlog.get_logger()

router = APIRouter(prefix="/api/chat", tags=["chat"])


class ChatRequest(BaseModel):
    message: str
    rfx_id: int | None = None
    history: list[dict[str, Any]] = []
    attachment_url: str | None = None
    attachment_name: str | None = None


class CreateRFxRequest(BaseModel):
    draft: dict[str, Any]


class DispatchConfirmRequest(BaseModel):
    rfx_id: int
    dispatch_plan: list[dict[str, Any]]


@router.post("")
async def chat(
    body: ChatRequest,
    session: Session = Depends(get_session),
    caller: AuthContext = Depends(get_current_user),
) -> JSONResponse:
    if caller.role not in (Role.BUYER, Role.VENDOR):
        raise HTTPException(403, "Chat not available for this role")

    from aeros.agents.procurement import ProcurementAgent

    agent = ProcurementAgent()
    chat_provider = get_chat_provider()
    chat_provider.user_id = caller.user_id
    chat_provider.rfx_id = body.rfx_id
    vision_provider = get_vision_provider()
    if vision_provider:
        vision_provider.user_id = caller.user_id
        vision_provider.rfx_id = body.rfx_id

    metadata: dict[str, Any] = {"history": body.history}
    if body.attachment_url:
        metadata["attachment_url"] = body.attachment_url
        metadata["attachment_name"] = body.attachment_name

    ctx = AgentContext(
        session=session,
        caller=caller,
        chat_provider=chat_provider,
        vision_provider=vision_provider,
        rfx_id=body.rfx_id,
        metadata=metadata,
    )

    try:
        result = await agent.run(ctx, body.message)
        data = result.data or {}

        # Bridge: extract tool results into top-level fields the frontend expects
        for tr in data.get("tool_results", []):
            if not tr.get("success"):
                continue
            tool_data = tr.get("data") or {}
            if tr["tool"] == "create_rfx" and "rfx_id" in tool_data:
                data["rfx_id"] = tool_data["rfx_id"]
                data["status"] = tool_data.get("status", "created")
            elif tr["tool"] == "list_vendors":
                data["suggested_vendors"] = tool_data
            elif tr["tool"] == "evaluate_offers":
                data["evaluation"] = tool_data

        return JSONResponse(
            content={
                "message": result.message,
                "data": data,
                "success": result.success,
            }
        )
    except Exception as e:
        logger.error("chat.error", error=str(e), traceback=traceback.format_exc())
        return JSONResponse(
            status_code=500,
            content={"message": f"AI error: {e}", "data": {}, "success": False},
        )


@router.post("/create-rfx")
async def create_rfx_from_draft(
    body: CreateRFxRequest,
    session: Session = Depends(get_session),
    caller: AuthContext = Depends(get_current_user),
) -> JSONResponse:
    if caller.role != Role.BUYER:
        raise HTTPException(403, "Only buyers can create RFx")

    draft = body.draft
    try:
        deadline_str = draft.get("response_deadline")
        deadline = None
        if deadline_str:
            with contextlib.suppress(ValueError, TypeError):
                deadline = datetime.fromisoformat(deadline_str)

        dw_start_str = draft.get("delivery_window_start")
        dw_end_str = draft.get("delivery_window_end")
        dw_start = None
        dw_end = None
        if dw_start_str:
            with contextlib.suppress(ValueError, TypeError):
                dw_start = datetime.fromisoformat(dw_start_str)
        if dw_end_str:
            with contextlib.suppress(ValueError, TypeError):
                dw_end = datetime.fromisoformat(dw_end_str)

        rfx = rfx_service.create_rfx(
            session,
            buyer_id=caller.user_id,
            title=draft.get("title", "Untitled RFx"),
            response_deadline=deadline,
            delivery_window_start=dw_start,
            delivery_window_end=dw_end,
            payment_terms_for_this_rfx=draft.get("payment_terms", "NET30"),
            delivery_terms_for_this_rfx=draft.get("delivery_terms", "doorstep"),
            currency_for_this_rfx=draft.get("currency", "INR"),
            notes_for_vendors=draft.get("notes_for_vendors"),
        )

        # Accept both "line_items" (frontend shape) and "items" (agent shape)
        line_items_data = draft.get("line_items") or draft.get("items") or []
        li_records = []
        for li in line_items_data:
            # Support multiple field name conventions from different agent responses
            sku_name = li.get("sku_name") or li.get("name") or li.get("item_name") or ""
            qty = li.get("qty") or li.get("quantity") or li.get("count") or 0
            unit = li.get("unit") or li.get("unit_override") or "pcs"
            target_price = (
                li.get("target_price")
                or li.get("est_unit_price")
                or li.get("last_price")
                or li.get("price")
            )

            # Try to find SKU by exact name, then fuzzy match
            sku_id = li.get("sku_id")
            sku = None
            if sku_id:
                sku = session.get(SKU, sku_id)
            if not sku and sku_name:
                sku = session.exec(select(SKU).where(SKU.name == sku_name)).first()
            if not sku and sku_name:
                sku = session.exec(
                    select(SKU).where(SKU.name.ilike(f"%{sku_name}%"))  # type: ignore[attr-defined]
                ).first()
            if sku:
                li_records.append(
                    {
                        "sku_id": sku.id,
                        "qty": int(qty),
                        "unit_override": unit,
                        "target_price": float(target_price) if target_price else None,
                    }
                )

        if li_records:
            rfx_service.add_line_items(session, rfx.id, li_records)  # type: ignore[arg-type]

        # Suggest vendors based on the SKUs in the draft
        from aeros.services import vendor_service

        vendors = vendor_service.list_vendors(session, caller.org_id or 0)
        suggested = []
        for v in vendors[:5]:
            suggested.append(
                {
                    "vendor_id": v.id,
                    "vendor_name": v.name,
                    "categories": v.category_ids_csv or "",
                    "recommended_channel": (
                        "in_app"
                        if v.vendor_user_id
                        else ("email" if v.primary_email else "telegram")
                    ),
                }
            )

        dispatch_plan = []
        for v in vendors[:5]:
            channel = "in_app" if v.vendor_user_id else ("email" if v.primary_email else "telegram")
            detail = v.primary_email or v.name
            dispatch_plan.append(
                {
                    "vendor_id": v.id,
                    "vendor_name": v.name,
                    "channel": channel,
                    "channel_detail": detail,
                }
            )

        return JSONResponse(
            content={
                "message": (
                    f"RFx '{rfx.title}' created successfully! Here are vendors you can dispatch to:"
                ),
                "data": {
                    "rfx_id": rfx.id,
                    "status": "created",
                    "suggested_vendors": suggested,
                    "dispatch_plan": dispatch_plan,
                },
                "success": True,
            }
        )
    except Exception as e:
        logger.error("create_rfx.error", error=str(e), traceback=traceback.format_exc())
        return JSONResponse(
            status_code=500,
            content={"message": f"Failed to create RFx: {e}", "data": {}, "success": False},
        )


@router.post("/dispatch")
async def dispatch_rfx(
    body: DispatchConfirmRequest,
    session: Session = Depends(get_session),
    caller: AuthContext = Depends(get_current_user),
) -> JSONResponse:
    if caller.role != Role.BUYER:
        raise HTTPException(403, "Only buyers can dispatch RFx")

    try:
        agent = SourcingAgent()
        chat_prov = get_chat_provider()
        chat_prov.user_id = caller.user_id
        chat_prov.rfx_id = body.rfx_id
        vis_prov = get_vision_provider()
        if vis_prov:
            vis_prov.user_id = caller.user_id
        ctx = AgentContext(
            session=session,
            caller=caller,
            chat_provider=chat_prov,
            vision_provider=vis_prov,
            rfx_id=body.rfx_id,
        )
        action = json.dumps(
            {
                "action": "confirm_dispatch",
                "rfx_id": body.rfx_id,
                "dispatch_plan": body.dispatch_plan,
            }
        )
        result = await agent.run(ctx, action)
        return JSONResponse(
            content={
                "message": result.message,
                "data": result.data,
                "success": result.success,
            }
        )
    except Exception as e:
        logger.error("dispatch.error", error=str(e), traceback=traceback.format_exc())
        return JSONResponse(
            status_code=500,
            content={"message": f"Dispatch failed: {e}", "data": {}, "success": False},
        )


@router.post("/upload")
async def chat_upload(
    file: UploadFile = File(...),
    caller: AuthContext = Depends(get_current_user),
) -> dict[str, Any]:
    """Upload a file from the buyer chat for AI extraction."""
    if caller.role != Role.BUYER:
        raise HTTPException(403, "Only buyers can upload via chat")

    content = await file.read()
    if len(content) > settings.max_upload_size_mb * 1024 * 1024:
        raise HTTPException(413, "File too large")

    sha = hashlib.sha256(content).hexdigest()[:12]
    upload_dir = os.path.join(settings.upload_dir, "chat", str(caller.user_id))
    os.makedirs(upload_dir, exist_ok=True)
    raw_name = os.path.basename(file.filename or "upload")
    filename = re.sub(r"[^\w.\-]", "_", raw_name)[:255]
    storage_path = os.path.join(upload_dir, f"{sha}_{filename}")
    with open(storage_path, "wb") as f:
        f.write(content)

    return {
        "url": f"/uploads/chat/{caller.user_id}/{sha}_{filename}",
        "file_url": storage_path,
        "name": filename,
    }
