"""Chat API — SSE-based conversational AI for buyer + vendor co-pilots."""

import json
import traceback

import structlog
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlmodel import Session

logger = structlog.get_logger()

from aeros.db import get_session
from aeros.models.user import Role
from aeros.security.auth_context import AuthContext, get_current_user
from aeros.agents.base import AgentContext
from aeros.agents.intake import IntakeAgent
from aeros.ai.factory import get_chat_provider, get_vision_provider

router = APIRouter(prefix="/api/chat", tags=["chat"])


class ChatRequest(BaseModel):
    message: str
    rfx_id: int | None = None
    history: list[dict] = []


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
        # TODO: VendorAgent
        return JSONResponse(content={
            "message": "Vendor co-pilot coming soon. For now, please use the reply and upload features.",
            "data": {},
            "success": True,
        })

    raise HTTPException(403, "Chat not available for this role")
