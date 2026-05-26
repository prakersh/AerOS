"""Offer service — CRUD + fusion for extracted offers."""

import json
from datetime import datetime, timezone

from sqlmodel import Session, select

from aeros.models.offer import Offer
from aeros.models.rfx import RFxRun
from aeros.services.audit_service import log_action


def create_offer_from_extraction(
    session: Session,
    rfx_id: int,
    vendor_id: int,
    extraction_data: dict,
    source_message_ids: list[int],
    is_late: bool = False,
) -> Offer:
    from aeros.models.rfx import RFxLineItem
    from aeros.models.sku import SKU

    # Check for existing offer (revision)
    existing = session.exec(
        select(Offer)
        .where(
            Offer.rfx_id == rfx_id,
            Offer.vendor_id == vendor_id,
            Offer.superseded_by_offer_id == None,  # noqa: E711
        )
        .order_by(Offer.revision_no.desc())  # type: ignore[union-attr]
    ).first()

    revision_no = 1
    if existing:
        revision_no = existing.revision_no + 1

    # Map extracted line items to RFx line items by fuzzy name matching
    rfx_line_items = list(
        session.exec(select(RFxLineItem).where(RFxLineItem.rfx_id == rfx_id)).all()
    )
    li_lookup: dict[str, int] = {}
    for rli in rfx_line_items:
        sku = session.get(SKU, rli.sku_id)
        if sku:
            li_lookup[sku.name.lower()] = rli.id  # type: ignore[arg-type]

    raw_items = extraction_data.get("line_items", [])
    mapped_items = []
    for item in raw_items:
        sku_name = (item.get("sku_name") or "").lower()
        line_item_id = None
        for name, lid in li_lookup.items():
            if name in sku_name or sku_name in name:
                line_item_id = lid
                break
        confidence_per_field = item.get("confidence_per_field", {})
        mapped_items.append({
            **item,
            "line_item_id": line_item_id,
            "confidence": confidence_per_field.get("unit_price", item.get("confidence")),
        })

    offer = Offer(
        rfx_id=rfx_id,
        vendor_id=vendor_id,
        line_items_json=json.dumps(mapped_items),
        total_quote=extraction_data.get("total_quote"),
        currency=extraction_data.get("currency", "INR"),
        lead_time_hours=extraction_data.get("lead_time_hours"),
        payment_terms=extraction_data.get("payment_terms"),
        delivery_terms=extraction_data.get("delivery_terms"),
        tax_treatment=extraction_data.get("tax_treatment"),
        gst_pct=extraction_data.get("gst_pct"),
        additional_charges_json=json.dumps(extraction_data.get("additional_charges", [])),
        vendor_remarks=extraction_data.get("vendor_remarks"),
        extraction_confidence_overall=extraction_data.get("confidence_overall", 0.0),
        source_message_ids_csv=",".join(str(mid) for mid in source_message_ids),
        raw_extraction_json=json.dumps(extraction_data),
        revision_no=revision_no,
        is_late=is_late,
        total_quote_inr=extraction_data.get("total_quote"),
    )
    session.add(offer)

    # Supersede previous offer
    if existing:
        existing.superseded_by_offer_id = offer.id
        session.add(existing)

    session.commit()
    session.refresh(offer)

    if existing:
        existing.superseded_by_offer_id = offer.id
        session.add(existing)
        session.commit()

    return offer


def get_offers_for_rfx(session: Session, rfx_id: int) -> list[Offer]:
    return list(
        session.exec(
            select(Offer)
            .where(Offer.rfx_id == rfx_id, Offer.superseded_by_offer_id == None)  # noqa: E711
            .order_by(Offer.vendor_id)
        ).all()
    )


def get_offer_history(session: Session, rfx_id: int, vendor_id: int) -> list[Offer]:
    return list(
        session.exec(
            select(Offer)
            .where(Offer.rfx_id == rfx_id, Offer.vendor_id == vendor_id)
            .order_by(Offer.revision_no)
        ).all()
    )


def override_offer_field(
    session: Session,
    offer_id: int,
    field_name: str,
    new_value: str,
    user_id: int,
) -> Offer:
    offer = session.get(Offer, offer_id)
    if not offer:
        raise ValueError("Offer not found")

    overrides = json.loads(offer.manual_overrides_json or "{}")
    overrides[field_name] = {
        "value": new_value,
        "overridden_by": user_id,
        "overridden_at": datetime.now(timezone.utc).isoformat(),
    }
    offer.manual_overrides_json = json.dumps(overrides)
    offer.updated_at = datetime.now(timezone.utc)
    session.add(offer)
    session.commit()
    session.refresh(offer)

    log_action(
        session,
        actor_user_id=user_id,
        actor_role="buyer",
        action="override_offer_field",
        entity_type="Offer",
        entity_id=str(offer_id),
        after={"field": field_name, "new_value": new_value},
    )
    return offer
