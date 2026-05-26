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
    return rfx


def list_rfx_for_buyer(session: Session, buyer_id: int) -> list[RFxRun]:
    return list(
        session.exec(
            select(RFxRun).where(RFxRun.buyer_id == buyer_id).order_by(RFxRun.created_at.desc())  # type: ignore[union-attr]
        ).all()
    )


def list_rfx_for_vendor(session: Session, vendor_id: int) -> list[dict]:
    rv_list = session.exec(
        select(RFxVendor).where(RFxVendor.vendor_id == vendor_id)
    ).all()
    results = []
    for rv in rv_list:
        rfx = session.get(RFxRun, rv.rfx_id)
        if rfx:
            results.append({
                "rfx": rfx,
                "vendor_status": rv.status.value,
                "dispatched_at": rv.dispatched_at,
            })
    return results


def get_rfx_with_details(session: Session, rfx_id: int) -> dict | None:
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
    return {
        "rfx": rfx,
        "line_items": line_items,
        "vendors": vendors,
        "offers": offers,
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
    return rfx
