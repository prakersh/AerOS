"""Chat API — conversational AI for buyer + vendor co-pilots, plus RFx actions."""

import json
import traceback
from datetime import datetime, timezone

import structlog
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlmodel import Session, select

logger = structlog.get_logger()

from aeros.db import get_session
from aeros.models.user import Role
from aeros.models.sku import SKU
from aeros.security.auth_context import AuthContext, get_current_user
from aeros.agents.base import AgentContext
from aeros.agents.intake import IntakeAgent
from aeros.agents.sourcing import SourcingAgent
from aeros.ai.factory import get_chat_provider, get_vision_provider
from aeros.services import rfx_service

router = APIRouter(prefix="/api/chat", tags=["chat"])


class ChatRequest(BaseModel):
    message: str
    rfx_id: int | None = None
    history: list[dict] = []


class CreateRFxRequest(BaseModel):
    draft: dict


class DispatchConfirmRequest(BaseModel):
    rfx_id: int
    dispatch_plan: list[dict]


@router.post("")
async def chat(
    body: ChatRequest,
    session: Session = Depends(get_session),
    caller: AuthContext = Depends(get_current_user),
):
    if caller.role == Role.BUYER:
        agent = IntakeAgent()
        chat_provider = get_chat_provider()
        vision_provider = get_vision_provider()

        ctx = AgentContext(
            session=session,
            caller=caller,
            chat_provider=chat_provider,
            vision_provider=vision_provider,
            rfx_id=body.rfx_id,
            metadata={"history": body.history},
        )

        try:
            result = await agent.run(ctx, body.message)
            return JSONResponse(content={
                "message": result.message,
                "data": result.data,
                "success": result.success,
            })
        except Exception as e:
            logger.error("chat.error", error=str(e), traceback=traceback.format_exc())
            return JSONResponse(
                status_code=500,
                content={"message": f"AI error: {e}", "data": {}, "success": False},
            )

    elif caller.role == Role.VENDOR:
        return JSONResponse(content={
            "message": "Vendor co-pilot coming soon. For now, please use the reply and upload features.",
            "data": {},
            "success": True,
        })

    raise HTTPException(403, "Chat not available for this role")


@router.post("/create-rfx")
async def create_rfx_from_draft(
    body: CreateRFxRequest,
    session: Session = Depends(get_session),
    caller: AuthContext = Depends(get_current_user),
):
    if caller.role != Role.BUYER:
        raise HTTPException(403, "Only buyers can create RFx")

    draft = body.draft
    try:
        deadline_str = draft.get("response_deadline")
        deadline = None
        if deadline_str:
            try:
                deadline = datetime.fromisoformat(deadline_str)
            except (ValueError, TypeError):
                pass

        dw_start_str = draft.get("delivery_window_start")
        dw_end_str = draft.get("delivery_window_end")
        dw_start = None
        dw_end = None
        if dw_start_str:
            try:
                dw_start = datetime.fromisoformat(dw_start_str)
            except (ValueError, TypeError):
                pass
        if dw_end_str:
            try:
                dw_end = datetime.fromisoformat(dw_end_str)
            except (ValueError, TypeError):
                pass

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

        line_items_data = draft.get("line_items", [])
        li_records = []
        for li in line_items_data:
            sku_name = li.get("sku_name", "")
            sku = session.exec(select(SKU).where(SKU.name == sku_name)).first()
            if not sku:
                sku = session.exec(
                    select(SKU).where(SKU.name.ilike(f"%{sku_name}%"))  # type: ignore[union-attr]
                ).first()
            if sku:
                li_records.append({
                    "sku_id": sku.id,
                    "qty": li.get("qty", 0),
                    "unit_override": li.get("unit"),
                    "target_price": li.get("target_price"),
                })

        if li_records:
            rfx_service.add_line_items(session, rfx.id, li_records)  # type: ignore[arg-type]

        return JSONResponse(content={
            "message": f"RFx '{rfx.title}' created successfully!",
            "data": {"rfx_id": rfx.id, "status": "created"},
            "success": True,
        })
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
):
    if caller.role != Role.BUYER:
        raise HTTPException(403, "Only buyers can dispatch RFx")

    try:
        agent = SourcingAgent()
        ctx = AgentContext(
            session=session,
            caller=caller,
            chat_provider=get_chat_provider(),
            vision_provider=get_vision_provider(),
            rfx_id=body.rfx_id,
        )
        action = json.dumps({
            "action": "confirm_dispatch",
            "rfx_id": body.rfx_id,
            "dispatch_plan": body.dispatch_plan,
        })
        result = await agent.run(ctx, action)
        return JSONResponse(content={
            "message": result.message,
            "data": result.data,
            "success": result.success,
        })
    except Exception as e:
        logger.error("dispatch.error", error=str(e), traceback=traceback.format_exc())
        return JSONResponse(
            status_code=500,
            content={"message": f"Dispatch failed: {e}", "data": {}, "success": False},
        )
