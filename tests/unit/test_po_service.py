"""Tests for po_service — PO lifecycle management."""

import pytest

from aeros.models.award import Award
from aeros.models.rfx import RFxRun, RFxStatus
from aeros.services.po_service import (
    create_award,
    create_po,
    get_po_by_award,
    list_pos_for_rfx,
)


@pytest.fixture
def rfx_run(session, buyer_org, buyer_user):
    """Create a minimal RFxRun for testing."""
    rfx = RFxRun(
        title="Test RFx",
        buyer_id=buyer_user.id,
        status=RFxStatus.CLOSED,
    )
    session.add(rfx)
    session.commit()
    session.refresh(rfx)
    return rfx


@pytest.fixture
def award(session, rfx_run, buyer_user):
    """Create an Award for testing."""
    a = Award(
        rfx_id=rfx_run.id,
        awarded_by_user_id=buyer_user.id,
        decisions_json='[{"vendor_id": 1, "items": [1, 2]}]',
    )
    session.add(a)
    session.commit()
    session.refresh(a)
    return a


class TestCreateAward:
    def test_create_award_success(self, session, rfx_run, buyer_user):
        """Should create an award with correct fields."""
        award = create_award(
            session,
            rfx_id=rfx_run.id,
            awarded_by_user_id=buyer_user.id,
            decisions_json='[{"vendor_id": 1}]',
        )
        assert award.id is not None
        assert award.rfx_id == rfx_run.id
        assert award.awarded_by_user_id == buyer_user.id

    def test_create_award_has_default_status(self, session, rfx_run, buyer_user):
        """Award should have default po_sent_status of 'pending'."""
        award = create_award(
            session,
            rfx_id=rfx_run.id,
            awarded_by_user_id=buyer_user.id,
        )
        assert award.po_sent_status == "pending"


class TestCreatePo:
    def test_create_po_success(self, session, award):
        """Should create a PurchaseOrder linked to an award."""
        po = create_po(
            session,
            award_id=award.id,
            vendor_id=1,
            po_number="PO-2026-001",
            total_amount=5000.0,
            currency="INR",
        )
        assert po.id is not None
        assert po.po_number == "PO-2026-001"
        assert po.award_id == award.id
        assert po.total_amount == 5000.0

    def test_create_po_default_currency(self, session, award):
        """PO should default to INR currency."""
        po = create_po(
            session,
            award_id=award.id,
            vendor_id=1,
            po_number="PO-2026-002",
            total_amount=100.0,
        )
        assert po.currency == "INR"


class TestGetPoByAward:
    def test_get_existing_po(self, session, award):
        """Should find PO by award_id."""
        create_po(session, award_id=award.id, vendor_id=1, po_number="PO-001", total_amount=100.0)
        found = get_po_by_award(session, award.id)
        assert found is not None
        assert found.po_number == "PO-001"

    def test_get_nonexistent_po(self, session, award):
        """Should return None when no PO exists for award."""
        found = get_po_by_award(session, award.id)
        assert found is None


class TestListPosForRfx:
    def test_list_empty(self, session, rfx_run):
        """Should return empty list when no awards exist."""
        result = list_pos_for_rfx(session, rfx_run.id)
        assert result == []

    def test_list_with_po(self, session, rfx_run, award):
        """Should return award info with PO details when PO exists."""
        create_po(session, award_id=award.id, vendor_id=1, po_number="PO-100", total_amount=999.0)
        result = list_pos_for_rfx(session, rfx_run.id)
        assert len(result) == 1
        assert result[0]["award_id"] == award.id
        assert result[0]["po_number"] == "PO-100"

    def test_list_without_po(self, session, rfx_run, award):
        """Should return award info with None PO when no PO created."""
        result = list_pos_for_rfx(session, rfx_run.id)
        assert len(result) == 1
        assert result[0]["award_id"] == award.id
        assert result[0]["po_number"] is None
