import contextlib
import json
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlmodel import Session, select

from aeros.db import get_session
from aeros.models.audit import AuditLog
from aeros.models.user import Role
from aeros.models.user_defaults import UserDefaults
from aeros.security.auth_context import AuthContext, require_role
from aeros.services import defaults_service, inventory_service, rfx_service, vendor_service

router = APIRouter(prefix="/api/buyer", tags=["buyer"])


# --- Helpers ---


def _raise_for_value_error(e: ValueError) -> None:
    msg = str(e)
    if "not found" in msg.lower():
        raise HTTPException(404, msg) from None
    raise HTTPException(400, msg) from None


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
) -> Any:
    return inventory_service.list_categories(session)


@router.get("/inventory")
def list_inventory(
    category_id: int | None = None,
    session: Session = Depends(get_session),
    caller: AuthContext = require_role(Role.BUYER, Role.ADMIN),
) -> Any:
    return inventory_service.list_skus(session, caller.org_id or 0, category_id)


@router.get("/inventory/search")
def search_inventory(
    q: str,
    session: Session = Depends(get_session),
    caller: AuthContext = require_role(Role.BUYER, Role.ADMIN),
) -> Any:
    return inventory_service.search_skus(session, caller.org_id or 0, q)


class UpdateSKURequest(BaseModel):
    reorder_point: float | None = None
    last_price: float | None = None


@router.put("/inventory/{sku_id}")
def update_sku(
    sku_id: int,
    body: UpdateSKURequest,
    session: Session = Depends(get_session),
    caller: AuthContext = require_role(Role.BUYER, Role.ADMIN),
) -> Any:
    from aeros.models.sku import SKU

    sku = session.get(SKU, sku_id)
    if not sku or sku.org_id != (caller.org_id or 0):
        raise HTTPException(404, "SKU not found")
    if body.reorder_point is not None:
        sku.reorder_point = body.reorder_point
    if body.last_price is not None:
        sku.last_price = body.last_price
    session.add(sku)
    session.commit()
    session.refresh(sku)
    return {
        "id": sku.id,
        "code": sku.code,
        "name": sku.name,
        "reorder_point": sku.reorder_point,
        "last_price": sku.last_price,
    }


# --- Vendors ---


@router.get("/vendors")
def list_vendors(
    session: Session = Depends(get_session),
    caller: AuthContext = require_role(Role.BUYER, Role.ADMIN),
) -> Any:
    return vendor_service.list_vendors(session, caller.org_id or 0)


@router.get("/vendors/{vendor_id}")
def get_vendor(
    vendor_id: int,
    session: Session = Depends(get_session),
    caller: AuthContext = require_role(Role.BUYER, Role.ADMIN),
) -> Any:
    v = vendor_service.get_vendor(session, vendor_id)
    if not v:
        raise HTTPException(404, "Vendor not found")
    return v


class ContactVendorRequest(BaseModel):
    message: str


@router.post("/vendors/{vendor_id}/contact")
def contact_vendor(
    vendor_id: int,
    body: ContactVendorRequest,
    session: Session = Depends(get_session),
    caller: AuthContext = require_role(Role.BUYER, Role.ADMIN),
) -> dict[str, Any]:
    from aeros.models.vendor import Vendor

    vendor = session.get(Vendor, vendor_id)
    if not vendor:
        raise HTTPException(404, "Vendor not found")
    from aeros.models.audit import AuditLog

    log = AuditLog(
        user_id=caller.user_id,
        action="contact_vendor",
        entity_type="vendor",
        entity_id=vendor_id,
        details_json=json.dumps({"message": body.message[:500], "vendor_name": vendor.name}),
    )
    session.add(log)
    session.commit()
    return {"ok": True, "vendor_name": vendor.name}


# --- RFx ---


@router.get("/rfx")
def list_rfx(
    session: Session = Depends(get_session),
    caller: AuthContext = require_role(Role.BUYER, Role.ADMIN),
) -> list[dict[str, Any]]:
    return rfx_service.list_rfx_for_buyer(session, caller.user_id)


@router.get("/rfx/{rfx_id}")
def get_rfx(
    rfx_id: int,
    session: Session = Depends(get_session),
    caller: AuthContext = require_role(Role.BUYER, Role.ADMIN),
) -> dict[str, Any]:
    _verify_rfx_ownership(session, rfx_id, caller)
    details = rfx_service.get_rfx_with_details(session, rfx_id)
    if not details:
        raise HTTPException(404, "RFx not found")
    return details


@router.get("/rfx/{rfx_id}/vendor-suggestions")
def vendor_suggestions(
    rfx_id: int,
    session: Session = Depends(get_session),
    caller: AuthContext = require_role(Role.BUYER, Role.ADMIN),
) -> Any:
    _verify_rfx_ownership(session, rfx_id, caller)
    try:
        return rfx_service.get_vendor_suggestions(session, rfx_id, caller.org_id or 0)
    except ValueError as e:
        _raise_for_value_error(e)


class VendorAssignment(BaseModel):
    vendor_id: int
    line_item_ids: list[int]


class AssignVendorsRequest(BaseModel):
    assignments: list[VendorAssignment]


@router.post("/rfx/{rfx_id}/assign-vendors")
def assign_vendors(
    rfx_id: int,
    body: AssignVendorsRequest,
    session: Session = Depends(get_session),
    caller: AuthContext = require_role(Role.BUYER),
) -> Any:
    _verify_rfx_ownership(session, rfx_id, caller)
    try:
        assignments = [a.model_dump() for a in body.assignments]
        return rfx_service.assign_vendors_to_items(session, rfx_id, caller.user_id, assignments)
    except ValueError as e:
        _raise_for_value_error(e)


class CancelRFxRequest(BaseModel):
    reason: str = ""


@router.post("/rfx/{rfx_id}/cancel")
def cancel_rfx(
    rfx_id: int,
    body: CancelRFxRequest,
    session: Session = Depends(get_session),
    caller: AuthContext = require_role(Role.BUYER),
) -> Any:
    _verify_rfx_ownership(session, rfx_id, caller)
    try:
        return rfx_service.cancel_rfx(session, rfx_id, caller.user_id, body.reason)
    except ValueError as e:
        _raise_for_value_error(e)


class AwardRequest(BaseModel):
    decisions: list[dict[str, Any]]


@router.post("/rfx/{rfx_id}/award")
async def award_rfx(
    rfx_id: int,
    body: AwardRequest,
    session: Session = Depends(get_session),
    caller: AuthContext = require_role(Role.BUYER),
) -> dict[str, Any]:
    _verify_rfx_ownership(session, rfx_id, caller)
    try:
        rfx_service.award_rfx(session, rfx_id, caller.user_id, body.decisions)
    except ValueError as e:
        _raise_for_value_error(e)

    # Trigger PO generation after successful award
    po_error = None
    try:
        from aeros.workers.po_render import render_and_send_po

        await render_and_send_po(rfx_id, body.decisions)
    except Exception as e:
        po_error = str(e)
        import structlog

        structlog.get_logger().error(
            "award.po_generation_failed",
            rfx_id=rfx_id,
            error=po_error,
        )

    result = rfx_service.get_rfx_with_details(session, rfx_id) or {}
    if po_error:
        result["po_generation_error"] = po_error
    return result


# --- Activity ---


@router.get("/activity")
def list_activity(
    limit: int = Query(default=50, ge=1, le=500),
    session: Session = Depends(get_session),
    caller: AuthContext = require_role(Role.BUYER, Role.ADMIN),
) -> list[dict[str, Any]]:
    logs = list(
        session.exec(
            select(AuditLog)
            .where(AuditLog.actor_user_id == caller.user_id)
            .order_by(AuditLog.created_at.desc())  # type: ignore[attr-defined]
            .limit(limit)
        ).all()
    )
    results = []
    for log in logs:
        after = {}
        if log.after_json:
            with contextlib.suppress(json.JSONDecodeError):
                after = json.loads(log.after_json)
        results.append(
            {
                "id": log.id,
                "action": log.action,
                "entity_type": log.entity_type,
                "entity_id": log.entity_id,
                "details": after,
                "created_at": log.created_at.isoformat() if log.created_at else "",
            }
        )
    return results


# --- Defaults ---


def _defaults_to_dict(d: UserDefaults) -> dict[str, Any]:
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
) -> dict[str, Any]:
    d = defaults_service.get_defaults(session, caller.user_id)
    if d:
        return _defaults_to_dict(d)
    d = defaults_service.ensure_defaults(session, caller.user_id)
    return _defaults_to_dict(d)


class UpdateDefaultsBody(BaseModel):
    payment_terms: str | None = None
    delivery_terms: str | None = None
    quote_validity_days: int | None = None
    currency: str | None = None
    tax_treatment: str | None = None
    delivery_window: str | None = None


@router.put("/defaults")
def update_defaults(
    body: UpdateDefaultsBody,
    session: Session = Depends(get_session),
    caller: AuthContext = require_role(Role.BUYER, Role.ADMIN),
) -> dict[str, Any]:
    field_map = {
        "payment_terms": "payment_terms_default",
        "delivery_terms": "delivery_terms_default",
        "quote_validity_days": "quote_validity_days_default",
        "currency": "currency_default",
        "tax_treatment": "tax_treatment_default",
        "delivery_window": "delivery_window_default",
    }
    updates = {}
    for api_field, model_field in field_map.items():
        val = getattr(body, api_field)
        if val is not None:
            updates[model_field] = val
    d = defaults_service.update_defaults(session, caller.user_id, **updates)
    return _defaults_to_dict(d)
