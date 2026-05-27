"""Integration tests for PO API endpoints."""

import pytest

from aeros.models.award import Award, PurchaseOrder
from aeros.models.organization import OrgType, Organization
from aeros.models.rfx import RFxRun, RFxStatus
from aeros.models.user import Role, User
from aeros.services.auth_service import hash_password


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def admin_user(session, buyer_org):
    user = User(
        email="admin@test.com",
        password_hash=hash_password("test123"),
        role=Role.ADMIN,
        display_name="Test Admin",
        org_id=buyer_org.id,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


@pytest.fixture
def admin_client(client, admin_user):
    resp = client.post(
        "/api/auth/login",
        json={"email": "admin@test.com", "password": "test123"},
    )
    assert resp.status_code == 200
    return client


@pytest.fixture
def rfx_run(session, buyer_org, buyer_user):
    rfx = RFxRun(
        title="Test RFx for PO",
        buyer_id=buyer_user.id,
        status=RFxStatus.CLOSED,
    )
    session.add(rfx)
    session.commit()
    session.refresh(rfx)
    return rfx


@pytest.fixture
def award(session, rfx_run, buyer_user):
    a = Award(
        rfx_id=rfx_run.id,
        awarded_by_user_id=buyer_user.id,
        decisions_json='[{"vendor_id": 1}]',
    )
    session.add(a)
    session.commit()
    session.refresh(a)
    return a


@pytest.fixture
def purchase_order(session, award):
    po = PurchaseOrder(
        award_id=award.id,
        vendor_id=1,
        po_number="PO-TEST-001",
        total_amount=5000.0,
        currency="INR",
    )
    session.add(po)
    session.commit()
    session.refresh(po)
    return po


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestGetPO:
    def test_get_po_success(self, admin_client, purchase_order, award):
        """GET /api/po/{id} should return PO details."""
        resp = admin_client.get(f"/api/po/{purchase_order.id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == purchase_order.id
        assert data["po_number"] == "PO-TEST-001"
        assert data["award_id"] == award.id

    def test_get_po_not_found(self, admin_client):
        """GET /api/po/99999 should return 404."""
        resp = admin_client.get("/api/po/99999")
        assert resp.status_code == 404

    def test_unauthenticated_cannot_get_po(self, client):
        """Unauthenticated user should get 401."""
        resp = client.get("/api/po/1")
        assert resp.status_code == 401


class TestDownloadPO:
    def test_download_po_no_pdf(self, admin_client, purchase_order):
        """Should return 404 when PO has no PDF."""
        resp = admin_client.get(f"/api/po/{purchase_order.id}/download")
        assert resp.status_code == 404

    def test_download_po_not_found(self, admin_client):
        """Should return 404 for nonexistent PO."""
        resp = admin_client.get("/api/po/99999/download")
        assert resp.status_code == 404


class TestListPOsForRfx:
    def test_list_pos_empty(self, admin_client, rfx_run):
        """GET /api/po/rfx/{id} should return empty list when no awards."""
        resp = admin_client.get(f"/api/po/rfx/{rfx_run.id}")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_list_pos_with_po(self, admin_client, rfx_run, purchase_order):
        """Should return awards with PO info."""
        resp = admin_client.get(f"/api/po/rfx/{rfx_run.id}")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["po_number"] == "PO-TEST-001"
        assert data[0]["po_id"] == purchase_order.id
