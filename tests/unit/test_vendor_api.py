"""Tests for vendor API — thread, submit-quote, and decline endpoints."""

import pytest
from sqlmodel import select

from aeros.models.organization import Organization, OrgType
from aeros.models.rfx import (
    Message,
    RFxLineItem,
    RFxRun,
    RFxVendor,
    RFxVendorStatus,
    Thread,
)
from aeros.models.sku import SKU, Category
from aeros.models.vendor import Vendor


@pytest.fixture
def vendor_org(session):
    org = Organization(name="VendorApiOrg", type=OrgType.VENDOR)
    session.add(org)
    session.commit()
    session.refresh(org)
    return org


@pytest.fixture
def vendor_with_user(session, buyer_org, vendor_org, vendor_user):
    v = Vendor(
        owning_buyer_org_id=buyer_org.id,
        vendor_org_id=vendor_org.id,
        name="API Test Vendor",
        primary_email="apivendor@test.com",
        vendor_user_id=vendor_user.id,
    )
    session.add(v)
    session.commit()
    session.refresh(v)
    return v


@pytest.fixture
def category(session):
    cat = Category(name="Produce", sort_order=1)
    session.add(cat)
    session.commit()
    session.refresh(cat)
    return cat


@pytest.fixture
def rfx_with_items(session, buyer_user, buyer_org, category):
    sku = SKU(
        org_id=buyer_org.id,
        code="PROD-001",
        name="Tomato",
        category_id=category.id,
        unit="kg",
    )
    session.add(sku)
    session.commit()
    session.refresh(sku)

    rfx = RFxRun(
        title="Produce RFQ",
        buyer_id=buyer_user.id,
        org_id=buyer_org.id,
        status="DISPATCHED",
    )
    session.add(rfx)
    session.commit()
    session.refresh(rfx)

    li = RFxLineItem(rfx_id=rfx.id, sku_id=sku.id, qty=100, unit_override="kg")
    session.add(li)
    session.commit()
    session.refresh(li)

    return rfx, li, sku


@pytest.fixture
def thread_with_vendor(session, rfx_with_items, vendor_with_user):
    rfx, li, _sku = rfx_with_items
    rv = RFxVendor(
        rfx_id=rfx.id,
        vendor_id=vendor_with_user.id,
        status=RFxVendorStatus.INVITED,
    )
    session.add(rv)
    session.commit()

    thread = Thread(rfx_id=rfx.id, vendor_id=vendor_with_user.id, status="open")
    session.add(thread)
    session.commit()
    session.refresh(thread)
    return thread, rv, rfx, li


def _login_vendor(client):
    resp = client.post(
        "/api/auth/login",
        json={"email": "vendor@test.com", "password": "test123"},
    )
    assert resp.status_code == 200


class TestGetThread:
    def test_returns_full_rfx_context(self, client, vendor_user, thread_with_vendor):
        _login_vendor(client)
        _thread, _rv, rfx, _li = thread_with_vendor
        resp = client.get(f"/api/vendor/rfx/{rfx.id}/thread")
        assert resp.status_code == 200

        data = resp.json()
        assert data["rfx_title"] == "Produce RFQ"
        assert data["rfx_status"] in ("dispatched", "DISPATCHED")
        assert len(data["line_items"]) == 1
        assert data["line_items"][0]["quantity"] == 100
        assert data["line_items"][0]["sku"] == "PROD-001"
        assert data["currency"] == "INR"
        assert isinstance(data["messages"], list)
        assert isinstance(data["attachments"], list)

    def test_marks_vendor_as_viewed(self, session, client, vendor_user, thread_with_vendor):
        _login_vendor(client)
        _thread, rv, rfx, _li = thread_with_vendor
        assert rv.status == RFxVendorStatus.INVITED

        client.get(f"/api/vendor/rfx/{rfx.id}/thread")

        session.refresh(rv)
        assert rv.status == RFxVendorStatus.VIEWED


class TestSubmitQuote:
    def test_creates_offer_from_structured_quote(
        self, session, client, vendor_user, thread_with_vendor
    ):
        _login_vendor(client)
        thread, rv, rfx, li = thread_with_vendor
        resp = client.post(
            f"/api/vendor/rfx/{rfx.id}/submit-quote",
            json={
                "line_items": [
                    {
                        "line_item_id": li.id,
                        "unit_price": 45.0,
                        "lead_time_days": 3,
                        "notes": "Fresh from farm",
                    }
                ],
                "payment_terms": "NET15",
                "delivery_terms": "doorstep",
                "vendor_remarks": "Can deliver same day",
            },
        )
        assert resp.status_code == 200

        data = resp.json()
        assert data["message"] == "Quote submitted successfully"
        assert data["revision_no"] == 1

        session.refresh(rv)
        assert rv.status == RFxVendorStatus.QUOTED

        msgs = list(session.exec(select(Message).where(Message.thread_id == thread.id)).all())
        assert len(msgs) == 1
        assert "Structured quote submitted" in msgs[0].body_text

    def test_empty_line_items_accepted(self, client, vendor_user, thread_with_vendor):
        _login_vendor(client)
        _thread, _rv, rfx, _li = thread_with_vendor
        resp = client.post(
            f"/api/vendor/rfx/{rfx.id}/submit-quote",
            json={"line_items": []},
        )
        assert resp.status_code == 200


class TestSubmitQuoteTotalCalculation:
    """Tests for Bug #1: vendor.py:338 uses `* 1` instead of quantity."""

    def test_total_uses_quantity_not_one(self, session, client, vendor_user, thread_with_vendor):
        """total_quote must be qty * unit_price, not just unit_price."""
        _login_vendor(client)
        _thread, _rv, rfx, li = thread_with_vendor
        resp = client.post(
            f"/api/vendor/rfx/{rfx.id}/submit-quote",
            json={
                "line_items": [
                    {
                        "line_item_id": li.id,
                        "unit_price": 50.0,
                    }
                ],
            },
        )
        assert resp.status_code == 200

        from aeros.models.offer import Offer

        offer = session.exec(select(Offer).where(Offer.rfx_id == rfx.id)).first()
        assert offer is not None
        # li.qty is 100, unit_price is 50 -> total should be 5000
        assert offer.total_quote == 5000.0

    def test_single_item_total(self, session, client, vendor_user, thread_with_vendor):
        """Single item: qty=100, price=25 -> total=2500."""
        _login_vendor(client)
        _thread, _rv, rfx, li = thread_with_vendor
        resp = client.post(
            f"/api/vendor/rfx/{rfx.id}/submit-quote",
            json={"line_items": [{"line_item_id": li.id, "unit_price": 25.0}]},
        )
        assert resp.status_code == 200

        from aeros.models.offer import Offer

        offer = session.exec(select(Offer).where(Offer.rfx_id == rfx.id)).first()
        assert offer is not None
        assert offer.total_quote == 2500.0

    def test_multiple_items_total(
        self, session, client, vendor_user, thread_with_vendor, category, buyer_org
    ):
        """Multiple items with different quantities and prices."""
        _login_vendor(client)
        _thread, _rv, rfx, li1 = thread_with_vendor

        sku2 = SKU(
            org_id=buyer_org.id,
            code="PROD-002",
            name="Onion",
            category_id=category.id,
            unit="kg",
        )
        session.add(sku2)
        session.commit()
        session.refresh(sku2)

        li2 = RFxLineItem(rfx_id=rfx.id, sku_id=sku2.id, qty=50, unit_override="kg")
        session.add(li2)
        session.commit()
        session.refresh(li2)

        resp = client.post(
            f"/api/vendor/rfx/{rfx.id}/submit-quote",
            json={
                "line_items": [
                    {"line_item_id": li1.id, "unit_price": 40.0},
                    {"line_item_id": li2.id, "unit_price": 30.0},
                ],
            },
        )
        assert resp.status_code == 200

        from aeros.models.offer import Offer

        offer = session.exec(select(Offer).where(Offer.rfx_id == rfx.id)).first()
        assert offer is not None
        # li1: 100 * 40 = 4000, li2: 50 * 30 = 1500 -> total = 5500
        assert offer.total_quote == 5500.0

    def test_zero_quantity_item(self, session, client, vendor_user, thread_with_vendor):
        """Edge case: qty=0 -> total contribution is 0."""
        _login_vendor(client)
        _thread, _rv, rfx, li = thread_with_vendor
        li.qty = 0
        session.add(li)
        session.commit()

        resp = client.post(
            f"/api/vendor/rfx/{rfx.id}/submit-quote",
            json={"line_items": [{"line_item_id": li.id, "unit_price": 100.0}]},
        )
        assert resp.status_code == 200

        from aeros.models.offer import Offer

        offer = session.exec(select(Offer).where(Offer.rfx_id == rfx.id)).first()
        assert offer is not None
        assert offer.total_quote == 0.0


class TestDecline:
    def test_decline_sets_status(self, session, client, vendor_user, thread_with_vendor):
        _login_vendor(client)
        _thread, rv, rfx, _li = thread_with_vendor
        resp = client.post(
            f"/api/vendor/rfx/{rfx.id}/decline",
            json={"reason": "Out of stock"},
        )
        assert resp.status_code == 200

        session.refresh(rv)
        assert rv.status == RFxVendorStatus.DECLINED

    def test_decline_nonexistent_rfx_returns_404(self, client, vendor_user, thread_with_vendor):
        """Declining a nonexistent RFx should return 404."""
        _login_vendor(client)
        resp = client.post(
            "/api/vendor/rfx/99999/decline",
            json={"reason": "test"},
        )
        assert resp.status_code == 404


class TestReply:
    """Tests for vendor reply endpoint."""

    def test_reply_creates_message(self, session, client, vendor_user, thread_with_vendor):
        """Reply should create a message in the thread."""
        _login_vendor(client)
        thread, _rv, rfx, _li = thread_with_vendor
        resp = client.post(
            f"/api/vendor/rfx/{rfx.id}/reply",
            json={"body_text": "We can supply this"},
        )
        assert resp.status_code == 200

        msgs = list(session.exec(select(Message).where(Message.thread_id == thread.id)).all())
        assert len(msgs) == 1
        assert msgs[0].body_text == "We can supply this"
        assert msgs[0].sender_kind == "vendor"


class TestUpload:
    """Tests for vendor file upload endpoint."""

    def test_upload_creates_attachment(self, session, client, vendor_user, thread_with_vendor):
        """Upload should create an attachment record."""
        _login_vendor(client)
        _thread, _rv, rfx, _li = thread_with_vendor
        resp = client.post(
            f"/api/vendor/rfx/{rfx.id}/upload",
            files={"file": ("quote.csv", b"item,price\nrice,45", "text/csv")},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["filename"] == "quote.csv"
        assert data["attachment_id"] is not None

    def test_upload_no_vendor_profile_returns_403(self, client, buyer_user):
        """User without vendor profile should get 403."""
        client.post(
            "/api/auth/login",
            json={"email": "buyer@test.com", "password": "test123"},
        )
        resp = client.post(
            "/api/vendor/rfx/1/upload",
            files={"file": ("test.txt", b"hello", "text/plain")},
        )
        assert resp.status_code == 403

    def test_upload_no_thread_returns_404(self, client, vendor_user, vendor_with_user):
        """Upload to nonexistent thread should return 404."""
        _login_vendor(client)
        resp = client.post(
            "/api/vendor/rfx/99999/upload",
            files={"file": ("test.txt", b"hello", "text/plain")},
        )
        assert resp.status_code == 404


class TestInbox:
    """Tests for vendor inbox endpoint."""

    def test_inbox_returns_list(self, client, vendor_user, thread_with_vendor):
        """Inbox should return a list of RFx invitations."""
        _login_vendor(client)
        resp = client.get("/api/vendor/inbox")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)

    def test_inbox_empty_for_vendor_with_no_invites(self, client, vendor_user):
        """Vendor with no invites should see empty inbox."""
        _login_vendor(client)
        resp = client.get("/api/vendor/inbox")
        assert resp.status_code == 200
        assert resp.json() == []


class TestThreadErrors:
    """Error cases for vendor thread endpoint."""

    def test_get_thread_no_vendor_profile_returns_403(self, client, buyer_user):
        """User without vendor profile should get 403."""
        client.post(
            "/api/auth/login",
            json={"email": "buyer@test.com", "password": "test123"},
        )
        resp = client.get("/api/vendor/rfx/1/thread")
        assert resp.status_code == 403

    def test_get_thread_no_thread_returns_404(self, client, vendor_user, vendor_with_user):
        """Nonexistent thread should return 404."""
        _login_vendor(client)
        resp = client.get("/api/vendor/rfx/99999/thread")
        assert resp.status_code == 404
