"""Integration tests for the full RFx lifecycle — draft via chat, create, list, detail, dispatch.

Covers the complete buyer demo flow:
1. Chat with LLM co-pilot to draft an RFx (LLM mocked)
2. Create the RFx from the draft
3. List RFx and verify it appears
4. Get RFx details with vendor_offers shape
5. Dispatch the RFx to vendors (LLM + email mocked)
"""

import json
from unittest.mock import AsyncMock, patch

import pytest

from aeros.ai.base import ChatResponse
from aeros.models.organization import OrgType, Organization
from aeros.models.sku import Category, SKU
from aeros.models.user import Role, User
from aeros.models.user_defaults import UserDefaults
from aeros.models.vendor import Vendor
from aeros.services.auth_service import hash_password


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def category(session):
    cat = Category(name="Grains", sort_order=1)
    session.add(cat)
    session.commit()
    session.refresh(cat)
    return cat


@pytest.fixture
def skus(session, buyer_org, category):
    items = [
        SKU(org_id=buyer_org.id, code="GRN-001", name="Basmati Rice", category_id=category.id, unit="kg"),
        SKU(org_id=buyer_org.id, code="GRN-002", name="Wheat Flour", category_id=category.id, unit="kg"),
    ]
    for s in items:
        session.add(s)
    session.commit()
    for s in items:
        session.refresh(s)
    return items


@pytest.fixture
def vendor_records(session, buyer_org):
    """Two vendor records owned by the buyer org."""
    vendors = []
    for i, (name, email) in enumerate([
        ("Agro Traders", "agro@test.com"),
        ("Fresh Supplies", "fresh@test.com"),
    ], start=1):
        v_org = Organization(name=f"VendorOrg{i}", type=OrgType.VENDOR)
        session.add(v_org)
        session.commit()
        session.refresh(v_org)

        v_user = User(
            email=email,
            password_hash=hash_password("test123"),
            role=Role.VENDOR,
            display_name=name,
            org_id=v_org.id,
        )
        session.add(v_user)
        session.commit()
        session.refresh(v_user)

        v = Vendor(
            owning_buyer_org_id=buyer_org.id,
            vendor_user_id=v_user.id,
            vendor_org_id=v_org.id,
            name=name,
            primary_email=email,
        )
        session.add(v)
        session.commit()
        session.refresh(v)
        vendors.append(v)
    return vendors


def _mock_chat_response(content: str) -> ChatResponse:
    """Create a mock ChatResponse with the given content."""
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


class TestRFxLifecycle:
    """Full RFx lifecycle integration tests — draft, create, list, detail, dispatch."""

    def test_chat_draft_rfx_via_llm(self, auth_client, skus):
        """POST /api/chat should return an AI-drafted RFx JSON when LLM is mocked."""
        draft_response = json.dumps({
            "message": "Here is your RFx draft for grains procurement.",
            "status": "draft_ready",
            "draft": {
                "title": "Weekly Grains Order",
                "line_items": [
                    {"sku_name": "Basmati Rice", "qty": 100, "unit": "kg", "target_price": 80},
                    {"sku_name": "Wheat Flour", "qty": 50, "unit": "kg", "target_price": 35},
                ],
                "payment_terms": "NET15",
                "currency": "INR",
                "response_deadline": "2026-06-10T23:59:00",
            },
        })

        mock_provider = AsyncMock()
        mock_provider.chat.return_value = _mock_chat_response(draft_response)

        with patch("aeros.api.chat.get_chat_provider", return_value=mock_provider), \
             patch("aeros.api.chat.get_vision_provider", return_value=None):
            resp = auth_client.post("/api/chat", json={
                "message": "I need 100kg Basmati Rice and 50kg Wheat Flour for next week",
                "history": [],
            })

        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert "draft" in data["data"] or "draft_ready" in data["data"].get("status", "")
        assert "Weekly Grains" in data["message"] or "grains" in data["message"].lower()

    def test_create_rfx_from_draft(self, auth_client, skus):
        """POST /api/chat/create-rfx should persist an RFx with line items."""
        draft = {
            "title": "Weekly Grains Order",
            "line_items": [
                {"sku_name": "Basmati Rice", "qty": 100, "unit": "kg", "target_price": 80},
                {"sku_name": "Wheat Flour", "qty": 50, "unit": "kg", "target_price": 35},
            ],
            "payment_terms": "NET15",
            "currency": "INR",
            "response_deadline": "2026-06-10T23:59:00",
            "delivery_terms": "ex-works",
        }
        resp = auth_client.post("/api/chat/create-rfx", json={"draft": draft})
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["data"]["rfx_id"] is not None
        assert data["data"]["status"] == "created"

    def test_list_rfx_shows_created(self, auth_client, skus):
        """GET /api/buyer/rfx should include the created RFx with line items."""
        # Create first
        draft = {
            "title": "Lifecycle List Test",
            "line_items": [
                {"sku_name": "Basmati Rice", "qty": 75, "unit": "kg"},
            ],
        }
        create_resp = auth_client.post("/api/chat/create-rfx", json={"draft": draft})
        assert create_resp.status_code == 200
        rfx_id = create_resp.json()["data"]["rfx_id"]

        # List
        resp = auth_client.get("/api/buyer/rfx")
        assert resp.status_code == 200
        rfx_list = resp.json()
        assert isinstance(rfx_list, list)
        assert len(rfx_list) >= 1

        found = [r for r in rfx_list if r["id"] == rfx_id]
        assert len(found) == 1
        assert found[0]["title"] == "Lifecycle List Test"
        assert found[0]["status"] == "drafting"
        assert len(found[0]["line_items"]) == 1

    def test_get_rfx_detail_with_vendor_offers(self, auth_client, skus):
        """GET /api/buyer/rfx/{id} should return details with vendor_offers key."""
        draft = {
            "title": "Detail Shape Test",
            "line_items": [
                {"sku_name": "Basmati Rice", "qty": 30, "unit": "kg", "target_price": 80},
            ],
            "payment_terms": "NET30",
            "delivery_terms": "doorstep",
            "currency": "INR",
        }
        create_resp = auth_client.post("/api/chat/create-rfx", json={"draft": draft})
        rfx_id = create_resp.json()["data"]["rfx_id"]

        resp = auth_client.get(f"/api/buyer/rfx/{rfx_id}")
        assert resp.status_code == 200
        detail = resp.json()
        assert detail["id"] == rfx_id
        assert detail["title"] == "Detail Shape Test"
        assert detail["status"] == "drafting"
        assert "vendor_offers" in detail
        assert isinstance(detail["vendor_offers"], list)
        assert "line_items" in detail
        assert len(detail["line_items"]) == 1
        assert detail["line_items"][0]["sku_name"] == "Basmati Rice"
        assert detail["line_items"][0]["qty"] == 30

    def test_dispatch_rfx_to_vendors(self, auth_client, skus, vendor_records):
        """POST /api/chat/dispatch should dispatch the RFx (LLM + email mocked)."""
        # Create RFx
        draft = {
            "title": "Dispatch Demo Order",
            "line_items": [
                {"sku_name": "Basmati Rice", "qty": 200, "unit": "kg"},
            ],
        }
        create_resp = auth_client.post("/api/chat/create-rfx", json={"draft": draft})
        rfx_id = create_resp.json()["data"]["rfx_id"]

        # Mock the LLM for sourcing agent + email sending
        sourcing_llm_response = json.dumps({
            "subject": "RFQ: Dispatch Demo Order",
            "summary": "We need 200kg Basmati Rice. Please quote by June 10.",
        })
        mock_provider = AsyncMock()
        mock_provider.chat.return_value = _mock_chat_response(sourcing_llm_response)

        dispatch_plan = [
            {"vendor_id": vendor_records[0].id, "channel": "in_app"},
            {"vendor_id": vendor_records[1].id, "channel": "email"},
        ]

        with patch("aeros.api.chat.get_chat_provider", return_value=mock_provider), \
             patch("aeros.api.chat.get_vision_provider", return_value=None), \
             patch("aeros.channels.email_out.aiosmtplib.send", new_callable=AsyncMock):
            resp = auth_client.post("/api/chat/dispatch", json={
                "rfx_id": rfx_id,
                "dispatch_plan": dispatch_plan,
            })

        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["data"]["dispatched_count"] == 2

        # Verify status changed to dispatched
        detail_resp = auth_client.get(f"/api/buyer/rfx/{rfx_id}")
        assert detail_resp.status_code == 200
        assert detail_resp.json()["status"] == "dispatched"
        assert len(detail_resp.json()["vendor_offers"]) == 2

    def test_dispatch_requires_buyer_role(self, client, session, skus):
        """POST /api/chat/dispatch should reject non-buyer users."""
        # Create a vendor user and login
        v_org = Organization(name="VendorDispatchOrg", type=OrgType.VENDOR)
        session.add(v_org)
        session.commit()
        session.refresh(v_org)

        v_user = User(
            email="vendor-dispatch@test.com",
            password_hash=hash_password("test123"),
            role=Role.VENDOR,
            display_name="Vendor Dispatch",
            org_id=v_org.id,
        )
        session.add(v_user)
        session.commit()

        client.post("/api/auth/login", json={
            "email": "vendor-dispatch@test.com",
            "password": "test123",
        })

        resp = client.post("/api/chat/dispatch", json={
            "rfx_id": 1,
            "dispatch_plan": [],
        })
        assert resp.status_code == 403

    def test_create_rfx_requires_buyer_role(self, client, session):
        """POST /api/chat/create-rfx should reject non-buyer users."""
        v_org = Organization(name="VendorCreateOrg", type=OrgType.VENDOR)
        session.add(v_org)
        session.commit()
        session.refresh(v_org)

        v_user = User(
            email="vendor-create@test.com",
            password_hash=hash_password("test123"),
            role=Role.VENDOR,
            display_name="Vendor Create",
            org_id=v_org.id,
        )
        session.add(v_user)
        session.commit()

        client.post("/api/auth/login", json={
            "email": "vendor-create@test.com",
            "password": "test123",
        })

        resp = client.post("/api/chat/create-rfx", json={
            "draft": {"title": "Should Fail"},
        })
        assert resp.status_code == 403

    def test_full_lifecycle_end_to_end(self, auth_client, skus, vendor_records):
        """End-to-end: draft -> create -> list -> detail -> dispatch -> verify status."""
        # Step 1: Draft via chat (mock LLM)
        draft_json = json.dumps({
            "message": "Draft ready for your review.",
            "status": "draft_ready",
            "draft": {
                "title": "E2E Lifecycle Test",
                "line_items": [
                    {"sku_name": "Basmati Rice", "qty": 150, "unit": "kg"},
                    {"sku_name": "Wheat Flour", "qty": 80, "unit": "kg"},
                ],
                "payment_terms": "NET30",
                "currency": "INR",
            },
        })
        mock_chat = AsyncMock()
        mock_chat.chat.return_value = _mock_chat_response(draft_json)

        with patch("aeros.api.chat.get_chat_provider", return_value=mock_chat), \
             patch("aeros.api.chat.get_vision_provider", return_value=None):
            chat_resp = auth_client.post("/api/chat", json={
                "message": "I need rice and wheat flour",
                "history": [],
            })
        assert chat_resp.status_code == 200
        assert chat_resp.json()["success"] is True

        # Step 2: Create the RFx
        create_draft = {
            "title": "E2E Lifecycle Test",
            "line_items": [
                {"sku_name": "Basmati Rice", "qty": 150, "unit": "kg"},
                {"sku_name": "Wheat Flour", "qty": 80, "unit": "kg"},
            ],
            "payment_terms": "NET30",
            "currency": "INR",
        }
        create_resp = auth_client.post("/api/chat/create-rfx", json={"draft": create_draft})
        assert create_resp.status_code == 200
        rfx_id = create_resp.json()["data"]["rfx_id"]

        # Step 3: List and find it
        list_resp = auth_client.get("/api/buyer/rfx")
        assert list_resp.status_code == 200
        titles = [r["title"] for r in list_resp.json()]
        assert "E2E Lifecycle Test" in titles

        # Step 4: Get detail
        detail_resp = auth_client.get(f"/api/buyer/rfx/{rfx_id}")
        assert detail_resp.status_code == 200
        detail = detail_resp.json()
        assert detail["status"] == "drafting"
        assert len(detail["line_items"]) == 2

        # Step 5: Dispatch
        sourcing_response = json.dumps({
            "subject": "RFQ: E2E Lifecycle Test",
            "summary": "We need 150kg Rice and 80kg Wheat Flour.",
        })
        mock_sourcing = AsyncMock()
        mock_sourcing.chat.return_value = _mock_chat_response(sourcing_response)

        dispatch_plan = [
            {"vendor_id": vendor_records[0].id, "channel": "in_app"},
            {"vendor_id": vendor_records[1].id, "channel": "in_app"},
        ]
        with patch("aeros.api.chat.get_chat_provider", return_value=mock_sourcing), \
             patch("aeros.api.chat.get_vision_provider", return_value=None), \
             patch("aeros.channels.email_out.aiosmtplib.send", new_callable=AsyncMock):
            dispatch_resp = auth_client.post("/api/chat/dispatch", json={
                "rfx_id": rfx_id,
                "dispatch_plan": dispatch_plan,
            })
        assert dispatch_resp.status_code == 200
        assert dispatch_resp.json()["data"]["dispatched_count"] == 2

        # Step 6: Verify final state
        final_resp = auth_client.get(f"/api/buyer/rfx/{rfx_id}")
        assert final_resp.status_code == 200
        final = final_resp.json()
        assert final["status"] == "dispatched"
        assert len(final["vendor_offers"]) == 2
        for vo in final["vendor_offers"]:
            assert vo["status"] == "invited"
            assert "vendor_name" in vo
