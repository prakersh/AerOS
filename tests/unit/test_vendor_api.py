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
