"""Integration tests for the vendor response flow — upload, extraction, offer creation.

Covers the vendor demo flow:
1. Vendor uploads a file to an RFx thread
2. Extraction runs (LLM mocked) and parses the file
3. An Offer is created from the extraction result
4. Buyer can see the comparison data in RFx details
"""

import io
import json
from unittest.mock import AsyncMock, patch

import pytest

from aeros.ai.base import ChatResponse
from aeros.models.organization import Organization, OrgType
from aeros.models.sku import SKU, Category
from aeros.models.user import Role, User
from aeros.models.vendor import Vendor
from aeros.services.auth_service import hash_password

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def category(session):
    cat = Category(name="Dairy", sort_order=1)
    session.add(cat)
    session.commit()
    session.refresh(cat)
    return cat


@pytest.fixture
def sku_milk(session, buyer_org, category):
    sku = SKU(
        org_id=buyer_org.id,
        code="DAI-001",
        name="Full Cream Milk",
        category_id=category.id,
        unit="ltr",
        last_price=55.0,
    )
    session.add(sku)
    session.commit()
    session.refresh(sku)
    return sku


@pytest.fixture
def vendor_org(session):
    org = Organization(name="MilkVendorOrg", type=OrgType.VENDOR)
    session.add(org)
    session.commit()
    session.refresh(org)
    return org


@pytest.fixture
def vendor_user_record(session, vendor_org, buyer_org):
    """A vendor user with both User and Vendor records."""
    user = User(
        email="milk-vendor@test.com",
        password_hash=hash_password("test123"),
        role=Role.VENDOR,
        display_name="Milk Vendor User",
        org_id=vendor_org.id,
    )
    session.add(user)
    session.commit()
    session.refresh(user)

    vendor = Vendor(
        owning_buyer_org_id=buyer_org.id,
        vendor_user_id=user.id,
        vendor_org_id=vendor_org.id,
        name="Milk Vendor Co",
        primary_email="milk-vendor@test.com",
    )
    session.add(vendor)
    session.commit()
    session.refresh(vendor)
    return user, vendor


@pytest.fixture
def rfx_with_thread(session, buyer_user, sku_milk, vendor_user_record):
    """An RFx in DISPATCHED status with a vendor thread ready for uploads."""
    from aeros.services import rfx_service

    _, vendor = vendor_user_record

    rfx = rfx_service.create_rfx(
        session,
        buyer_id=buyer_user.id,
        title="Milk Procurement Q3",
    )
    rfx_service.add_line_items(
        session,
        rfx.id,
        [
            {"sku_id": sku_milk.id, "qty": 500, "unit_override": "ltr", "target_price": 55.0},
        ],
    )

    # Invite vendor + create thread
    rfx_service.invite_vendor(session, rfx.id, vendor.id, "dummy-token-hash")
    rfx_service.dispatch_rfx(session, rfx.id, buyer_user.id)

    return rfx


@pytest.fixture
def vendor_auth_client(client, vendor_user_record):
    """TestClient authenticated as the milk vendor."""
    _user, _ = vendor_user_record
    resp = client.post(
        "/api/auth/login",
        json={"email": "milk-vendor@test.com", "password": "test123"},
    )
    assert resp.status_code == 200
    return client


def _mock_chat_response(content: str) -> ChatResponse:
    return ChatResponse(
        content=content,
        input_tokens=100,
        output_tokens=50,
        model="mock-model",
        finish_reason="stop",
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestVendorUploadFlow:
    """Tests for vendor file upload, extraction, and offer creation."""

    def test_vendor_sees_rfx_in_inbox(self, vendor_auth_client, rfx_with_thread):
        """Vendor should see the dispatched RFx in their inbox."""
        resp = vendor_auth_client.get("/api/vendor/inbox")
        assert resp.status_code == 200
        inbox = resp.json()
        assert len(inbox) >= 1
        rfx_ids = [r["rfx_id"] for r in inbox]
        assert rfx_with_thread.id in rfx_ids
        item = next(r for r in inbox if r["rfx_id"] == rfx_with_thread.id)
        assert item["title"] == "Milk Procurement Q3"

    def test_vendor_can_view_thread(self, vendor_auth_client, rfx_with_thread):
        """Vendor should be able to see the thread."""
        resp = vendor_auth_client.get(f"/api/vendor/rfx/{rfx_with_thread.id}/thread")
        assert resp.status_code == 200
        messages = resp.json()
        assert isinstance(messages, list)

    def test_vendor_upload_triggers_extraction_and_offer(
        self, vendor_auth_client, rfx_with_thread, vendor_user_record, sku_milk
    ):
        """Upload should trigger extraction (mocked) and create an Offer."""
        _, _vendor = vendor_user_record

        # Mock the extraction LLM — two calls: first pass + gleaning pass
        extraction_result = json.dumps(
            {
                "line_items": [
                    {
                        "sku_name": "Full Cream Milk",
                        "qty": 500,
                        "unit": "ltr",
                        "unit_price": 52.0,
                        "total": 26000.0,
                        "confidence_per_field": {"unit_price": 0.95, "qty": 0.98},
                    },
                ],
                "total_quote": 26000.0,
                "currency": "INR",
                "payment_terms": "NET15",
                "delivery_terms": "doorstep",
                "lead_time_hours": 24,
                "confidence_overall": 0.92,
            }
        )
        mock_provider = AsyncMock()
        mock_provider.chat.return_value = _mock_chat_response(extraction_result)

        # Create a simple CSV test file
        csv_content = b"Item,Price/ltr,Qty\nFull Cream Milk,52,500\n"

        with (
            patch("aeros.ai.factory.get_chat_provider", return_value=mock_provider),
            patch("aeros.ai.factory.get_vision_provider", return_value=None),
        ):
            resp = vendor_auth_client.post(
                f"/api/vendor/rfx/{rfx_with_thread.id}/upload",
                files={"file": ("quote.csv", io.BytesIO(csv_content), "text/csv")},
            )

        assert resp.status_code == 200
        data = resp.json()
        assert "message_id" in data
        assert "attachment_id" in data
        assert data["filename"] == "quote.csv"

    def test_buyer_sees_vendor_offer_after_upload(
        self, client, session, buyer_user, rfx_with_thread, vendor_user_record, sku_milk
    ):
        """After vendor uploads, buyer should see comparison data in RFx details."""
        _, _vendor = vendor_user_record

        # Login as vendor and upload
        client.post(
            "/api/auth/login",
            json={
                "email": "milk-vendor@test.com",
                "password": "test123",
            },
        )

        extraction_result = json.dumps(
            {
                "line_items": [
                    {
                        "sku_name": "Full Cream Milk",
                        "qty": 500,
                        "unit": "ltr",
                        "unit_price": 52.0,
                        "total": 26000.0,
                        "confidence_per_field": {"unit_price": 0.95},
                    },
                ],
                "total_quote": 26000.0,
                "currency": "INR",
                "payment_terms": "NET15",
                "lead_time_hours": 24,
                "confidence_overall": 0.92,
            }
        )
        mock_provider = AsyncMock()
        mock_provider.chat.return_value = _mock_chat_response(extraction_result)

        csv_content = b"Item,Price/ltr,Qty\nFull Cream Milk,52,500\n"

        with (
            patch("aeros.ai.factory.get_chat_provider", return_value=mock_provider),
            patch("aeros.ai.factory.get_vision_provider", return_value=None),
        ):
            upload_resp = client.post(
                f"/api/vendor/rfx/{rfx_with_thread.id}/upload",
                files={"file": ("quote.csv", io.BytesIO(csv_content), "text/csv")},
            )
        assert upload_resp.status_code == 200

        # Now login as buyer and check details
        client.post(
            "/api/auth/login",
            json={
                "email": "buyer@test.com",
                "password": "test123",
            },
        )

        detail_resp = client.get(f"/api/buyer/rfx/{rfx_with_thread.id}")
        assert detail_resp.status_code == 200
        detail = detail_resp.json()

        assert len(detail["vendor_offers"]) >= 1
        vo = detail["vendor_offers"][0]
        assert vo["vendor_name"] == "Milk Vendor Co"
        # After upload + extraction, the vendor lane should be QUOTED
        assert vo["status"] == "quoted"
        assert vo["total_quote"] == 26000.0
        assert vo["payment_terms"] == "NET15"

    def test_vendor_uploads_list(self, vendor_auth_client, rfx_with_thread, vendor_user_record):
        """GET /api/vendor/rfx/{id}/uploads should list uploaded files."""
        _, _vendor = vendor_user_record

        extraction_result = json.dumps(
            {
                "line_items": [],
                "confidence_overall": 0.5,
            }
        )
        mock_provider = AsyncMock()
        mock_provider.chat.return_value = _mock_chat_response(extraction_result)

        csv_content = b"Item,Price\nTest,10\n"

        with (
            patch("aeros.ai.factory.get_chat_provider", return_value=mock_provider),
            patch("aeros.ai.factory.get_vision_provider", return_value=None),
        ):
            vendor_auth_client.post(
                f"/api/vendor/rfx/{rfx_with_thread.id}/upload",
                files={"file": ("prices.csv", io.BytesIO(csv_content), "text/csv")},
            )

        resp = vendor_auth_client.get(f"/api/vendor/rfx/{rfx_with_thread.id}/uploads")
        assert resp.status_code == 200
        uploads = resp.json()
        assert len(uploads) >= 1
        assert uploads[0]["filename"] == "prices.csv"
        assert uploads[0]["size_bytes"] > 0

    def test_vendor_can_reply_to_thread(self, vendor_auth_client, rfx_with_thread):
        """POST /api/vendor/rfx/{id}/reply should add a message."""
        resp = vendor_auth_client.post(
            f"/api/vendor/rfx/{rfx_with_thread.id}/reply",
            json={"body_text": "We can deliver by tomorrow morning."},
        )
        assert resp.status_code == 200

        # Verify message appears in thread
        thread_resp = vendor_auth_client.get(f"/api/vendor/rfx/{rfx_with_thread.id}/thread")
        assert thread_resp.status_code == 200
        messages = thread_resp.json()
        texts = [m["body_text"] for m in messages]
        assert "We can deliver by tomorrow morning." in texts

    def test_vendor_can_decline_rfx(self, vendor_auth_client, rfx_with_thread):
        """POST /api/vendor/rfx/{id}/decline should update status to declined."""
        resp = vendor_auth_client.post(
            f"/api/vendor/rfx/{rfx_with_thread.id}/decline",
            json={"reason": "Out of stock"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "declined"
        assert data["decline_reason"] == "Out of stock"

    def test_upload_to_nonexistent_thread_fails(self, vendor_auth_client):
        """Uploading to an RFx the vendor is not invited to should fail."""
        csv_content = b"test,data\n"
        resp = vendor_auth_client.post(
            "/api/vendor/rfx/99999/upload",
            files={"file": ("test.csv", io.BytesIO(csv_content), "text/csv")},
        )
        assert resp.status_code == 404
