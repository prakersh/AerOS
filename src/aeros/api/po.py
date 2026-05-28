"""PO download and listing API."""

import os
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlmodel import Session, select

from aeros.db import get_session
from aeros.models.award import Award, PurchaseOrder
from aeros.models.user import Role
from aeros.security.auth_context import AuthContext, require_role

router = APIRouter(prefix="/api/po", tags=["po"])


@router.get("/{po_id}")
def get_po(
    po_id: int,
    session: Session = Depends(get_session),
    caller: AuthContext = require_role(Role.BUYER, Role.ADMIN),
) -> dict[str, Any]:
    """Get PO details by ID."""
    po = session.get(PurchaseOrder, po_id)
    if not po:
        raise HTTPException(404, "PO not found")
    session.get(Award, po.award_id)
    return {
        "id": po.id,
        "po_number": po.po_number,
        "award_id": po.award_id,
        "vendor_id": po.vendor_id,
        "total_amount": po.total_amount,
        "currency": po.currency,
        "pdf_path": po.pdf_path,
        "issued_at": po.issued_at.isoformat() if po.issued_at else "",
    }


@router.get("/{po_id}/download")
def download_po(
    po_id: int,
    session: Session = Depends(get_session),
    caller: AuthContext = require_role(Role.BUYER, Role.VENDOR, Role.ADMIN),
) -> FileResponse:
    """Download PO PDF file."""
    po = session.get(PurchaseOrder, po_id)
    if not po:
        raise HTTPException(404, "PO not found")
    if not po.pdf_path or not os.path.exists(po.pdf_path):
        raise HTTPException(404, "PO PDF not found")
    # Bug #7 fix: serve HTML fallback as text/html, not application/pdf
    is_html = po.pdf_path.endswith(".html")
    media_type = "text/html" if is_html else "application/pdf"
    ext = "html" if is_html else "pdf"
    return FileResponse(
        po.pdf_path,
        media_type=media_type,
        filename=f"PO_{po.po_number}.{ext}",
    )


@router.get("/rfx/{rfx_id}")
def list_pos_for_rfx(
    rfx_id: int,
    session: Session = Depends(get_session),
    caller: AuthContext = require_role(Role.BUYER, Role.ADMIN),
) -> list[dict[str, Any]]:
    """List all POs for a given RFx."""
    awards = list(session.exec(select(Award).where(Award.rfx_id == rfx_id)).all())
    result = []
    for award in awards:
        po = session.exec(select(PurchaseOrder).where(PurchaseOrder.award_id == award.id)).first()
        result.append(
            {
                "award_id": award.id,
                "vendor_id": po.vendor_id if po else None,
                "po_number": po.po_number if po else None,
                "has_pdf": bool(po and po.pdf_path),
                "po_id": po.id if po else None,
            }
        )
    return result
