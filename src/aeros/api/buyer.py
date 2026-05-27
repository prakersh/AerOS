import json

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlmodel import Session, select

from aeros.db import get_session
from aeros.models.user import Role, User
from aeros.models.audit import AuditLog
from aeros.models.user_defaults import UserDefaults
from aeros.security.auth_context import AuthContext, require_role
from aeros.services import inventory_service, vendor_service, rfx_service, defaults_service

router = APIRouter(prefix="/api/buyer", tags=["buyer"])


# --- Helpers ---


def _verify_rfx_ownership(session: Session, rfx_id: int, caller: AuthContext) -> None:
    """Verify the caller owns this RFx. Admins bypass.

    Args:
        session: Database session.
        rfx_id: The RFx to check.
        caller: Authenticated user context.

    Raises:
        HTTPException: 404 if RFx not found, 403 if not the owner.
    """
    if caller.role == Role.ADMIN:
        return
    details = rfx_service.get_rfx_with_details(session, rfx_id)
    if not details:
        raise HTTPException(404, "RFx not found")
    if details.get("buyer_id") and details["buyer_id"] != caller.user_id:
        raise HTTPException(403, "Not your RFx")


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
    _verify_rfx_ownership(session, rfx_id, caller)
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
    _verify_rfx_ownership(session, rfx_id, caller)
    try:
        return rfx_service.cancel_rfx(session, rfx_id, caller.user_id, body.reason)
    except ValueError as e:
        msg = str(e)
        if "not found" in msg.lower():
            raise HTTPException(404, msg)
        raise HTTPException(400, msg)


class AwardRequest(BaseModel):
    decisions: list[dict]


@router.post("/rfx/{rfx_id}/award")
def award_rfx(
    rfx_id: int,
    body: AwardRequest,
    session: Session = Depends(get_session),
    caller: AuthContext = require_role(Role.BUYER),
):
    _verify_rfx_ownership(session, rfx_id, caller)
    try:
        return rfx_service.award_rfx(session, rfx_id, caller.user_id, body.decisions)
    except ValueError as e:
        msg = str(e)
        if "not found" in msg.lower():
            raise HTTPException(404, msg)
        raise HTTPException(400, msg)


# --- Activity ---


@router.get("/activity")
def list_activity(
    limit: int = Query(default=50, ge=1, le=500),
    session: Session = Depends(get_session),
    caller: AuthContext = require_role(Role.BUYER, Role.ADMIN),
):
    logs = list(
        session.exec(
            select(AuditLog)
            .where(AuditLog.actor_user_id == caller.user_id)
            .order_by(AuditLog.created_at.desc())  # type: ignore[union-attr]
            .limit(limit)
        ).all()
    )
    results = []
    for log in logs:
        after = {}
        if log.after_json:
            try:
                after = json.loads(log.after_json)
            except json.JSONDecodeError:
                pass
        results.append({
            "id": log.id,
            "action": log.action,
            "entity_type": log.entity_type,
            "entity_id": log.entity_id,
            "details": after,
            "created_at": log.created_at.isoformat() if log.created_at else "",
        })
    return results


# --- Defaults ---


def _defaults_to_dict(d: UserDefaults) -> dict:
    """Convert a UserDefaults model to the API response dict.

    Args:
        d: The UserDefaults instance.

    Returns:
        Dictionary with default procurement settings.
    """
    return {
        "payment_terms": d.payment_terms_default,
        "delivery_terms": d.delivery_terms_default,
        "quote_validity_days": d.quote_validity_days_default,
        "currency": d.currency_default,
        "tax_treatment": d.tax_treatment_default,
        "delivery_window": d.delivery_window_default,
    }


@router.get("/defaults")
def get_defaults(
    session: Session = Depends(get_session),
    caller: AuthContext = require_role(Role.BUYER, Role.ADMIN),
):
    d = defaults_service.get_defaults(session, caller.user_id)
    if d:
        return _defaults_to_dict(d)
    d = defaults_service.ensure_defaults(session, caller.user_id)
    return _defaults_to_dict(d)
