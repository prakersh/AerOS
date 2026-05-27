"""PO lifecycle management — award creation, PO creation and queries."""

from sqlmodel import Session, select

from aeros.models.award import Award, PurchaseOrder


def create_award(
    session: Session,
    rfx_id: int,
    awarded_by_user_id: int,
    decisions_json: str = "[]",
    po_pdf_path: str | None = None,
) -> Award:
    """Create a new award for an RFx.

    Args:
        session: Database session.
        rfx_id: RFx run to award.
        awarded_by_user_id: User who made the award decision.
        decisions_json: JSON string of award decisions.
        po_pdf_path: Optional path to the PO PDF.

    Returns:
        The created Award.
    """
    award = Award(
        rfx_id=rfx_id,
        awarded_by_user_id=awarded_by_user_id,
        decisions_json=decisions_json,
        po_pdf_path=po_pdf_path,
    )
    session.add(award)
    session.commit()
    session.refresh(award)
    return award


def create_po(
    session: Session,
    award_id: int,
    vendor_id: int,
    po_number: str,
    total_amount: float,
    currency: str = "INR",
    terms_json: str = "{}",
    line_items_json: str = "[]",
    pdf_path: str | None = None,
) -> PurchaseOrder:
    """Create a PurchaseOrder linked to an award.

    Args:
        session: Database session.
        award_id: Award this PO belongs to.
        vendor_id: Vendor receiving the PO.
        po_number: Unique PO number.
        total_amount: Total order amount.
        currency: Currency code (default INR).
        terms_json: JSON string of terms.
        line_items_json: JSON string of line items.
        pdf_path: Optional path to generated PDF.

    Returns:
        The created PurchaseOrder.
    """
    po = PurchaseOrder(
        award_id=award_id,
        vendor_id=vendor_id,
        po_number=po_number,
        total_amount=total_amount,
        currency=currency,
        terms_json=terms_json,
        line_items_json=line_items_json,
        pdf_path=pdf_path,
    )
    session.add(po)
    session.commit()
    session.refresh(po)
    return po


def get_po_by_award(session: Session, award_id: int) -> PurchaseOrder | None:
    """Find a PurchaseOrder by its award_id.

    Args:
        session: Database session.
        award_id: The award ID to look up.

    Returns:
        PurchaseOrder if found, else None.
    """
    return session.exec(
        select(PurchaseOrder).where(PurchaseOrder.award_id == award_id)
    ).first()


def list_pos_for_rfx(session: Session, rfx_id: int) -> list[dict]:
    """List all awards and their POs for a given RFx.

    Args:
        session: Database session.
        rfx_id: The RFx run ID.

    Returns:
        List of dicts with award and PO info.
    """
    awards = list(session.exec(select(Award).where(Award.rfx_id == rfx_id)).all())
    result = []
    for award in awards:
        po = get_po_by_award(session, award.id)
        result.append({
            "award_id": award.id,
            "vendor_id": po.vendor_id if po else None,
            "po_number": po.po_number if po else None,
            "pdf_path": po.pdf_path if po else None,
            "issued_at": po.issued_at.isoformat() if po and po.issued_at else "",
        })
    return result
