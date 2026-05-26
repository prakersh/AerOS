import json
from datetime import datetime, timezone

from sqlmodel import Session, select

from aeros.models.rfx import (
    RFxLineItem,
    RFxRun,
    RFxStatus,
    RFxVendor,
    RFxVendorStatus,
    Thread,
)
from aeros.models.offer import Offer
from aeros.services.audit_service import log_action


def create_rfx(session: Session, buyer_id: int, title: str, **kwargs) -> RFxRun:
    rfx = RFxRun(buyer_id=buyer_id, title=title, **kwargs)
    session.add(rfx)
    session.commit()
    session.refresh(rfx)
    log_action(
        session,
        actor_user_id=buyer_id,
        actor_role="buyer",
        action="create_rfx",
        entity_type="RFxRun",
        entity_id=str(rfx.id),
        after={"title": title, "status": rfx.status.value},
    )
    session.refresh(rfx)
    return rfx


def add_line_items(session: Session, rfx_id: int, items: list[dict]) -> list[RFxLineItem]:
    line_items = []
    for item in items:
        li = RFxLineItem(rfx_id=rfx_id, **item)
        session.add(li)
        line_items.append(li)
    session.commit()
    for li in line_items:
        session.refresh(li)
    return line_items


def invite_vendor(session: Session, rfx_id: int, vendor_id: int, token_hash: str) -> RFxVendor:
    rv = RFxVendor(rfx_id=rfx_id, vendor_id=vendor_id, correlation_token_hash=token_hash)
    session.add(rv)
    thread = Thread(rfx_id=rfx_id, vendor_id=vendor_id)
    session.add(thread)
    session.commit()
    session.refresh(rv)
    return rv


def dispatch_rfx(session: Session, rfx_id: int, buyer_id: int) -> RFxRun:
    rfx = session.get(RFxRun, rfx_id)
    if not rfx:
        raise ValueError("RFx not found")
    rfx.status = RFxStatus.DISPATCHED
    rfx.updated_at = datetime.now(timezone.utc)
    session.add(rfx)

    vendors = session.exec(select(RFxVendor).where(RFxVendor.rfx_id == rfx_id)).all()
    for rv in vendors:
        rv.dispatched_at = datetime.now(timezone.utc)
        session.add(rv)

    session.commit()
    session.refresh(rfx)
    log_action(
        session,
        actor_user_id=buyer_id,
        actor_role="buyer",
        action="dispatch_rfx",
        entity_type="RFxRun",
        entity_id=str(rfx_id),
        after={"status": "dispatched", "vendor_count": len(list(vendors))},
    )
    session.refresh(rfx)
    return rfx


def cancel_rfx(session: Session, rfx_id: int, user_id: int, reason: str) -> RFxRun:
    rfx = session.get(RFxRun, rfx_id)
    if not rfx:
        raise ValueError("RFx not found")
    rfx.status = RFxStatus.CANCELLED
    rfx.cancelled_at = datetime.now(timezone.utc)
    rfx.cancelled_by_user_id = user_id
    rfx.cancelled_reason = reason
    rfx.updated_at = datetime.now(timezone.utc)
    session.add(rfx)
    session.commit()
    session.refresh(rfx)
    log_action(
        session,
        actor_user_id=user_id,
        actor_role="buyer",
        action="cancel_rfx",
        entity_type="RFxRun",
        entity_id=str(rfx_id),
        after={"status": "cancelled", "reason": reason},
    )
    session.refresh(rfx)
    return rfx


def list_rfx_for_buyer(session: Session, buyer_id: int) -> list[dict]:
    from aeros.models.sku import SKU

    rfx_list = list(
        session.exec(
            select(RFxRun).where(RFxRun.buyer_id == buyer_id).order_by(RFxRun.created_at.desc())  # type: ignore[union-attr]
        ).all()
    )
    results = []
    for rfx in rfx_list:
        vendors = list(session.exec(select(RFxVendor).where(RFxVendor.rfx_id == rfx.id)).all())
        line_items = list(session.exec(select(RFxLineItem).where(RFxLineItem.rfx_id == rfx.id)).all())
        li_dicts = []
        for li in line_items:
            sku = session.get(SKU, li.sku_id)
            li_dicts.append({
                "id": li.id,
                "sku_code": sku.code if sku else "",
                "sku_name": sku.name if sku else "",
                "qty": li.qty,
                "unit": li.unit_override or (sku.unit if sku else ""),
                "target_price": li.target_price,
            })
        results.append({
            "id": rfx.id,
            "title": rfx.title,
            "status": rfx.status.value,
            "vendor_count": len(vendors),
            "deadline": rfx.response_deadline.isoformat() if rfx.response_deadline else "",
            "created_at": rfx.created_at.isoformat() if rfx.created_at else "",
            "line_items": li_dicts,
        })
    return results


def list_rfx_for_vendor(session: Session, vendor_id: int) -> list[dict]:
    rv_list = session.exec(
        select(RFxVendor).where(RFxVendor.vendor_id == vendor_id)
    ).all()
    results = []
    for rv in rv_list:
        rfx = session.get(RFxRun, rv.rfx_id)
        if rfx:
            results.append({
                "rfx_id": rfx.id,
                "title": rfx.title,
                "status": rv.status.value,
                "dispatched_at": rv.dispatched_at.isoformat() if rv.dispatched_at else "",
                "deadline": rfx.response_deadline.isoformat() if rfx.response_deadline else "",
            })
    return results


def get_rfx_with_details(session: Session, rfx_id: int) -> dict | None:
    from aeros.models.sku import SKU
    from aeros.models.vendor import Vendor as VendorModel

    rfx = session.get(RFxRun, rfx_id)
    if not rfx:
        return None

    line_items = list(
        session.exec(select(RFxLineItem).where(RFxLineItem.rfx_id == rfx_id)).all()
    )
    vendors = list(
        session.exec(select(RFxVendor).where(RFxVendor.rfx_id == rfx_id)).all()
    )
    offers = list(
        session.exec(
            select(Offer)
            .where(Offer.rfx_id == rfx_id, Offer.superseded_by_offer_id == None)  # noqa: E711
        ).all()
    )

    li_dicts = []
    for li in line_items:
        sku = session.get(SKU, li.sku_id)
        li_dicts.append({
            "id": li.id,
            "sku_code": sku.code if sku else "",
            "sku_name": sku.name if sku else "",
            "qty": li.qty,
            "unit": li.unit_override or (sku.unit if sku else ""),
            "target_price": li.target_price,
        })

    offer_lookup: dict[int, Offer] = {o.vendor_id: o for o in offers}
    vendor_offers = []
    for rv in vendors:
        vendor = session.get(VendorModel, rv.vendor_id)
        offer = offer_lookup.get(rv.vendor_id)
        vo: dict = {
            "vendor_id": rv.vendor_id,
            "vendor_name": vendor.name if vendor else f"Vendor #{rv.vendor_id}",
            "status": rv.status.value,
            "decline_reason": rv.decline_reason,
        }
        if offer:
            vo["total_quote"] = offer.total_quote
            vo["lead_time"] = f"{offer.lead_time_hours}h" if offer.lead_time_hours else None
            vo["payment_terms"] = offer.payment_terms
            try:
                offer_items = json.loads(offer.line_items_json)
                vo["line_items"] = [
                    {
                        "line_item_id": oi.get("line_item_id"),
                        "unit_price": oi.get("unit_price", 0),
                        "confidence": oi.get("confidence"),
                    }
                    for oi in offer_items
                ]
            except (json.JSONDecodeError, TypeError):
                vo["line_items"] = []
        vendor_offers.append(vo)

    delivery_window = ""
    if rfx.delivery_window_start and rfx.delivery_window_end:
        delivery_window = f"{rfx.delivery_window_start.isoformat()} – {rfx.delivery_window_end.isoformat()}"

    return {
        "id": rfx.id,
        "title": rfx.title,
        "status": rfx.status.value,
        "delivery_window": delivery_window,
        "deadline": rfx.response_deadline.isoformat() if rfx.response_deadline else "",
        "created_at": rfx.created_at.isoformat() if rfx.created_at else "",
        "line_items": li_dicts,
        "vendor_offers": vendor_offers,
    }


def decline_rfx_vendor(
    session: Session, rfx_id: int, vendor_id: int, reason: str
) -> RFxVendor:
    rv = session.exec(
        select(RFxVendor).where(RFxVendor.rfx_id == rfx_id, RFxVendor.vendor_id == vendor_id)
    ).first()
    if not rv:
        raise ValueError("Vendor not invited to this RFx")
    rv.status = RFxVendorStatus.DECLINED
    rv.decline_reason = reason
    rv.declined_at = datetime.now(timezone.utc)
    session.add(rv)
    session.commit()
    session.refresh(rv)
    return rv


def award_rfx(session: Session, rfx_id: int, buyer_id: int, decisions: list[dict]) -> RFxRun:
    from aeros.models.award import Award
    rfx = session.get(RFxRun, rfx_id)
    if not rfx:
        raise ValueError("RFx not found")
    rfx.status = RFxStatus.AWARDED
    rfx.updated_at = datetime.now(timezone.utc)
    session.add(rfx)

    award = Award(
        rfx_id=rfx_id,
        awarded_by_user_id=buyer_id,
        decisions_json=json.dumps(decisions),
    )
    session.add(award)
    session.commit()
    session.refresh(rfx)
    session.refresh(award)
    log_action(
        session,
        actor_user_id=buyer_id,
        actor_role="buyer",
        action="award_rfx",
        entity_type="RFxRun",
        entity_id=str(rfx_id),
        after={"status": "awarded", "decisions_count": len(decisions)},
    )
    session.refresh(rfx)
    return rfx
