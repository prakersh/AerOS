import json
from datetime import UTC, datetime

from sqlmodel import Session, select

from aeros.models.offer import Offer
from aeros.models.rfx import (
    RFxLineItem,
    RFxRun,
    RFxStatus,
    RFxVendor,
    RFxVendorStatus,
    Thread,
)
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


def invite_vendor(
    session: Session,
    rfx_id: int,
    vendor_id: int,
    token_hash: str,
    line_item_ids: list[int] | None = None,
) -> RFxVendor:
    existing = session.exec(
        select(RFxVendor).where(RFxVendor.rfx_id == rfx_id, RFxVendor.vendor_id == vendor_id)
    ).first()
    if existing:
        return existing
    line_item_ids_json = json.dumps(line_item_ids) if line_item_ids is not None else None
    rv = RFxVendor(
        rfx_id=rfx_id,
        vendor_id=vendor_id,
        correlation_token_hash=token_hash,
        line_item_ids_json=line_item_ids_json,
    )
    session.add(rv)
    existing_thread = session.exec(
        select(Thread).where(Thread.rfx_id == rfx_id, Thread.vendor_id == vendor_id)
    ).first()
    if not existing_thread:
        thread = Thread(rfx_id=rfx_id, vendor_id=vendor_id)
        session.add(thread)
    session.commit()
    session.refresh(rv)
    return rv


def dispatch_rfx(session: Session, rfx_id: int, buyer_id: int) -> RFxRun:
    rfx = session.get(RFxRun, rfx_id)
    if not rfx:
        raise ValueError("RFx not found")
    if rfx.status == RFxStatus.DISPATCHED:
        return rfx
    rfx.status = RFxStatus.DISPATCHED
    rfx.updated_at = datetime.now(UTC)
    session.add(rfx)

    vendors = session.exec(select(RFxVendor).where(RFxVendor.rfx_id == rfx_id)).all()
    for rv in vendors:
        rv.dispatched_at = datetime.now(UTC)
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
    rfx.cancelled_at = datetime.now(UTC)
    rfx.cancelled_by_user_id = user_id
    rfx.cancelled_reason = reason
    rfx.updated_at = datetime.now(UTC)
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
        line_items = list(
            session.exec(select(RFxLineItem).where(RFxLineItem.rfx_id == rfx.id)).all()
        )
        li_dicts = []
        for li in line_items:
            sku = session.get(SKU, li.sku_id)
            li_dicts.append(
                {
                    "id": li.id,
                    "sku_code": sku.code if sku else "",
                    "sku_name": sku.name if sku else "",
                    "qty": li.qty,
                    "unit": li.unit_override or (sku.unit if sku else ""),
                    "target_price": li.target_price,
                }
            )
        results.append(
            {
                "id": rfx.id,
                "title": rfx.title,
                "status": rfx.status.value,
                "vendor_count": len(vendors),
                "deadline": rfx.response_deadline.isoformat() if rfx.response_deadline else "",
                "created_at": rfx.created_at.isoformat() if rfx.created_at else "",
                "line_items": li_dicts,
            }
        )
    return results


def list_rfx_for_vendor(session: Session, vendor_id: int) -> list[dict]:
    from aeros.models.user import User

    rv_list = session.exec(select(RFxVendor).where(RFxVendor.vendor_id == vendor_id)).all()
    results = []
    for rv in rv_list:
        rfx = session.get(RFxRun, rv.rfx_id)
        if rfx:
            buyer = session.get(User, rfx.buyer_id)
            item_count = len(
                list(session.exec(select(RFxLineItem).where(RFxLineItem.rfx_id == rfx.id)).all())
            )
            results.append(
                {
                    "rfx_id": rfx.id,
                    "title": rfx.title,
                    "status": rv.status.value,
                    "buyer_name": buyer.display_name if buyer else None,
                    "item_count": item_count,
                    "dispatched_at": rv.dispatched_at.isoformat() if rv.dispatched_at else "",
                    "deadline": (
                        rfx.response_deadline.isoformat() if rfx.response_deadline else ""
                    ),
                }
            )
    return results


def get_rfx_with_details(session: Session, rfx_id: int) -> dict | None:
    from aeros.models.sku import SKU
    from aeros.models.vendor import Vendor as VendorModel

    rfx = session.get(RFxRun, rfx_id)
    if not rfx:
        return None

    line_items = list(session.exec(select(RFxLineItem).where(RFxLineItem.rfx_id == rfx_id)).all())
    vendors = list(session.exec(select(RFxVendor).where(RFxVendor.rfx_id == rfx_id)).all())
    offers = list(
        session.exec(
            select(Offer).where(Offer.rfx_id == rfx_id, Offer.superseded_by_offer_id == None)  # noqa: E711
        ).all()
    )

    li_dicts = []
    for li in line_items:
        sku = session.get(SKU, li.sku_id)
        li_dicts.append(
            {
                "id": li.id,
                "sku_code": sku.code if sku else "",
                "sku_name": sku.name if sku else "",
                "qty": li.qty,
                "unit": li.unit_override or (sku.unit if sku else ""),
                "target_price": li.target_price,
            }
        )

    offer_lookup: dict[int, Offer] = {o.vendor_id: o for o in offers}
    vendor_offers = []
    dispatch_plan: list[dict] = []
    for rv in vendors:
        vendor = session.get(VendorModel, rv.vendor_id)
        offer = offer_lookup.get(rv.vendor_id)

        # Parse assigned line item IDs (null means all items)
        assigned_ids: list[int] | None = None
        if rv.line_item_ids_json:
            try:
                assigned_ids = json.loads(rv.line_item_ids_json)
            except (json.JSONDecodeError, TypeError):
                assigned_ids = None

        vo: dict = {
            "vendor_id": rv.vendor_id,
            "vendor_name": vendor.name if vendor else f"Vendor #{rv.vendor_id}",
            "status": rv.status.value,
            "decline_reason": rv.decline_reason,
            "assigned_line_item_ids": assigned_ids,
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

        # Build dispatch plan entry
        dispatch_plan.append(
            {
                "vendor_id": rv.vendor_id,
                "vendor_name": vendor.name if vendor else f"Vendor #{rv.vendor_id}",
                "assigned_line_item_ids": assigned_ids,
                "assigned_item_count": len(assigned_ids) if assigned_ids else len(li_dicts),
            }
        )

    delivery_window = ""
    if rfx.delivery_window_start and rfx.delivery_window_end:
        dw_start = rfx.delivery_window_start.isoformat()
        dw_end = rfx.delivery_window_end.isoformat()
        delivery_window = f"{dw_start} - {dw_end}"

    return {
        "id": rfx.id,
        "buyer_id": rfx.buyer_id,
        "title": rfx.title,
        "status": rfx.status.value,
        "delivery_window": delivery_window,
        "deadline": rfx.response_deadline.isoformat() if rfx.response_deadline else "",
        "created_at": rfx.created_at.isoformat() if rfx.created_at else "",
        "line_items": li_dicts,
        "vendor_offers": vendor_offers,
        "dispatch_plan": dispatch_plan,
    }


def decline_rfx_vendor(session: Session, rfx_id: int, vendor_id: int, reason: str) -> RFxVendor:
    rv = session.exec(
        select(RFxVendor).where(RFxVendor.rfx_id == rfx_id, RFxVendor.vendor_id == vendor_id)
    ).first()
    if not rv:
        raise ValueError("Vendor not invited to this RFx")
    rv.status = RFxVendorStatus.DECLINED
    rv.decline_reason = reason
    rv.declined_at = datetime.now(UTC)
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
    rfx.updated_at = datetime.now(UTC)
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


def get_vendor_suggestions(session: Session, rfx_id: int, buyer_org_id: int) -> dict:
    """Suggest vendors for each line item based on category matching and performance."""
    from aeros.models.sku import SKU
    from aeros.models.vendor import Vendor

    rfx = session.get(RFxRun, rfx_id)
    if not rfx:
        raise ValueError("RFx not found")

    line_items = list(session.exec(select(RFxLineItem).where(RFxLineItem.rfx_id == rfx_id)).all())
    if not line_items:
        return {"suggestions": [], "unassigned_items": []}

    # Build line item info with category IDs
    li_info: list[dict] = []
    for li in line_items:
        sku = session.get(SKU, li.sku_id)
        li_info.append(
            {
                "line_item_id": li.id,
                "sku_code": sku.code if sku else "",
                "sku_name": sku.name if sku else "",
                "qty": li.qty,
                "unit": li.unit_override or (sku.unit if sku else ""),
                "category_id": sku.category_id if sku else None,
            }
        )

    # Get all vendors for this buyer org
    all_vendors = list(
        session.exec(
            select(Vendor)
            .where(Vendor.owning_buyer_org_id == buyer_org_id)
            .order_by(Vendor.preferred_rank, Vendor.name)
        ).all()
    )

    # For each vendor, find matching items
    suggestions: list[dict] = []
    all_assigned_item_ids: set[int] = set()

    for vendor in all_vendors:
        vendor_cat_ids = set()
        if vendor.category_ids_csv:
            for cid in vendor.category_ids_csv.split(","):
                cid = cid.strip()
                if cid.isdigit():
                    vendor_cat_ids.add(int(cid))

        matching_items: list[dict] = []
        for li in li_info:
            if li["category_id"] is not None and li["category_id"] in vendor_cat_ids:
                matching_items.append(
                    {
                        "line_item_id": li["line_item_id"],
                        "sku_code": li["sku_code"],
                        "sku_name": li["sku_name"],
                        "qty": li["qty"],
                        "unit": li["unit"],
                    }
                )

        if not matching_items:
            continue

        # Score: category match ratio * 0.5 + normalized performance * 0.3 + preferred_rank * 0.2
        match_ratio = len(matching_items) / len(li_info)
        perf_score = vendor.performance_score or 0.0
        # Normalize preferred_rank: lower is better, max assumed 100
        rank_score = max(0, 1.0 - (vendor.preferred_rank / 100.0))
        composite_score = round(match_ratio * 0.5 + (perf_score / 5.0) * 0.3 + rank_score * 0.2, 2)

        for mi in matching_items:
            all_assigned_item_ids.add(mi["line_item_id"])

        suggestions.append(
            {
                "vendor_id": vendor.id,
                "vendor_name": vendor.name,
                "matching_items": matching_items,
                "match_score": composite_score,
                "performance_score": perf_score,
            }
        )

    # Sort by match_score descending
    suggestions.sort(key=lambda s: s["match_score"], reverse=True)

    # Find unassigned items
    unassigned_items: list[dict] = []
    for li in li_info:
        if li["line_item_id"] not in all_assigned_item_ids:
            unassigned_items.append(
                {
                    "line_item_id": li["line_item_id"],
                    "sku_code": li["sku_code"],
                    "sku_name": li["sku_name"],
                }
            )

    return {"suggestions": suggestions, "unassigned_items": unassigned_items}


def assign_vendors_to_items(
    session: Session,
    rfx_id: int,
    buyer_id: int,
    assignments: list[dict],
) -> dict:
    """Assign specific line items to vendors. Creates/updates RFxVendor records."""
    rfx = session.get(RFxRun, rfx_id)
    if not rfx:
        raise ValueError("RFx not found")

    # Validate all line item IDs belong to this RFx
    valid_line_items = {
        li.id for li in session.exec(select(RFxLineItem).where(RFxLineItem.rfx_id == rfx_id)).all()
    }

    result_assignments: list[dict] = []
    for assignment in assignments:
        vendor_id = assignment["vendor_id"]
        line_item_ids = assignment["line_item_ids"]

        # Validate line item IDs
        invalid_ids = [lid for lid in line_item_ids if lid not in valid_line_items]
        if invalid_ids:
            raise ValueError(f"Line item IDs {invalid_ids} do not belong to RFx {rfx_id}")

        # Find or create the RFxVendor record
        rv = session.exec(
            select(RFxVendor).where(RFxVendor.rfx_id == rfx_id, RFxVendor.vendor_id == vendor_id)
        ).first()

        line_item_ids_json = json.dumps(line_item_ids)

        if rv:
            rv.line_item_ids_json = line_item_ids_json
            session.add(rv)
        else:
            # Create a new RFxVendor with a placeholder token hash
            from aeros.channels.correlation import generate_correlation_token

            _, token_hash = generate_correlation_token(rfx_id, vendor_id)
            rv = RFxVendor(
                rfx_id=rfx_id,
                vendor_id=vendor_id,
                correlation_token_hash=token_hash,
                line_item_ids_json=line_item_ids_json,
            )
            session.add(rv)
            # Also ensure a thread exists
            existing_thread = session.exec(
                select(Thread).where(Thread.rfx_id == rfx_id, Thread.vendor_id == vendor_id)
            ).first()
            if not existing_thread:
                session.add(Thread(rfx_id=rfx_id, vendor_id=vendor_id))

        result_assignments.append(
            {
                "vendor_id": vendor_id,
                "line_item_ids": line_item_ids,
            }
        )

    session.commit()

    log_action(
        session,
        actor_user_id=buyer_id,
        actor_role="buyer",
        action="assign_vendors_to_items",
        entity_type="RFxRun",
        entity_id=str(rfx_id),
        after={"assignments": result_assignments},
    )

    return {"rfx_id": rfx_id, "assignments": result_assignments}
