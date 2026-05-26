from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session

from aeros.db import get_session
from aeros.models.user import Role
from aeros.security.auth_context import AuthContext, require_role
from aeros.services import inventory_service, vendor_service, rfx_service

router = APIRouter(prefix="/api/buyer", tags=["buyer"])


# --- Inventory ---


@router.get("/categories")
def list_categories(
    session: Session = Depends(get_session),
    caller: AuthContext = require_role(Role.BUYER, Role.ADMIN),
):
    return inventory_service.list_categories(session)


@router.get("/inventory")
def list_inventory(
    category_id: int | None = None,
    session: Session = Depends(get_session),
    caller: AuthContext = require_role(Role.BUYER, Role.ADMIN),
):
    return inventory_service.list_skus(session, caller.org_id or 0, category_id)


@router.get("/inventory/search")
def search_inventory(
    q: str,
    session: Session = Depends(get_session),
    caller: AuthContext = require_role(Role.BUYER, Role.ADMIN),
):
    return inventory_service.search_skus(session, caller.org_id or 0, q)


# --- Vendors ---


@router.get("/vendors")
def list_vendors(
    session: Session = Depends(get_session),
    caller: AuthContext = require_role(Role.BUYER, Role.ADMIN),
):
    return vendor_service.list_vendors(session, caller.org_id or 0)


@router.get("/vendors/{vendor_id}")
def get_vendor(
    vendor_id: int,
    session: Session = Depends(get_session),
    caller: AuthContext = require_role(Role.BUYER, Role.ADMIN),
):
    v = vendor_service.get_vendor(session, vendor_id)
    if not v:
        raise HTTPException(404, "Vendor not found")
    return v


# --- RFx ---


@router.get("/rfx")
def list_rfx(
    session: Session = Depends(get_session),
    caller: AuthContext = require_role(Role.BUYER, Role.ADMIN),
):
    return rfx_service.list_rfx_for_buyer(session, caller.user_id)


@router.get("/rfx/{rfx_id}")
def get_rfx(
    rfx_id: int,
    session: Session = Depends(get_session),
    caller: AuthContext = require_role(Role.BUYER, Role.ADMIN),
):
    details = rfx_service.get_rfx_with_details(session, rfx_id)
    if not details:
        raise HTTPException(404, "RFx not found")
    return details


class CancelRFxRequest(BaseModel):
    reason: str = ""


@router.post("/rfx/{rfx_id}/cancel")
def cancel_rfx(
    rfx_id: int,
    body: CancelRFxRequest,
    session: Session = Depends(get_session),
    caller: AuthContext = require_role(Role.BUYER),
):
    try:
        return rfx_service.cancel_rfx(session, rfx_id, caller.user_id, body.reason)
    except ValueError as e:
        raise HTTPException(404, str(e))


class AwardRequest(BaseModel):
    decisions: list[dict]


@router.post("/rfx/{rfx_id}/award")
def award_rfx(
    rfx_id: int,
    body: AwardRequest,
    session: Session = Depends(get_session),
    caller: AuthContext = require_role(Role.BUYER),
):
    try:
        return rfx_service.award_rfx(session, rfx_id, caller.user_id, body.decisions)
    except ValueError as e:
        raise HTTPException(404, str(e))
