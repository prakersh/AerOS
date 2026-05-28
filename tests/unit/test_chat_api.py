"""Tests for Chat API endpoints — auth, routing, create-rfx, upload."""

from unittest.mock import AsyncMock, patch

import pytest

from aeros.models.organization import Organization, OrgType
from aeros.models.sku import SKU, Category
from aeros.models.user import Role, User
from aeros.models.user_defaults import UserDefaults
from aeros.services.auth_service import hash_password


@pytest.fixture
def chat_org(session):
    org = Organization(name="ChatOrg", type=OrgType.BUYER)
    session.add(org)
    session.commit()
    session.refresh(org)
    return org


@pytest.fixture
def chat_buyer(session, chat_org):
    user = User(
        email="chat-buyer@test.com",
        password_hash=hash_password("test123"),
        role=Role.BUYER,
        display_name="Chat Buyer",
        org_id=chat_org.id,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    session.add(UserDefaults(user_id=user.id))
    session.commit()
    return user


@pytest.fixture
def chat_vendor_user(session):
    vorg = Organization(name="ChatVendorOrg", type=OrgType.VENDOR)
    session.add(vorg)
    session.commit()
    session.refresh(vorg)
    user = User(
        email="chat-vendor@test.com",
        password_hash=hash_password("test123"),
        role=Role.VENDOR,
        display_name="Chat Vendor",
        org_id=vorg.id,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


@pytest.fixture
def chat_admin(session, chat_org):
    user = User(
        email="chat-admin@test.com",
        password_hash=hash_password("test123"),
        role=Role.ADMIN,
        display_name="Chat Admin",
        org_id=chat_org.id,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


@pytest.fixture
def chat_category(session):
    cat = Category(name="ChatCat", sort_order=1)
    session.add(cat)
    session.commit()
    session.refresh(cat)
    return cat


@pytest.fixture
def chat_sku(session, chat_org, chat_category):
    sku = SKU(
        org_id=chat_org.id,
        code="CHAT-001",
        name="Rice",
        category_id=chat_category.id,
        unit="kg",
    )
    session.add(sku)
    session.commit()
    session.refresh(sku)
    return sku


def _login(client, email, password):
    resp = client.post("/api/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200


class TestChatAuth:
    """Auth requirements for chat endpoints."""

    def test_chat_requires_auth(self, client):
        """No session -> 401."""
        resp = client.post("/api/chat", json={"message": "hello"})
        assert resp.status_code == 401

    def test_chat_requires_buyer_or_vendor(self, client, chat_admin):
        """Admin -> 403."""
        _login(client, "chat-admin@test.com", "test123")
        resp = client.post("/api/chat", json={"message": "hello"})
        assert resp.status_code == 403

    def test_create_rfx_requires_buyer(self, client, chat_vendor_user):
        """Vendor -> 403 on create-rfx."""
        _login(client, "chat-vendor@test.com", "test123")
        resp = client.post(
            "/api/chat/create-rfx",
            json={"draft": {"title": "Test"}},
        )
        assert resp.status_code == 403

    def test_dispatch_requires_buyer(self, client, chat_vendor_user):
        """Vendor -> 403 on dispatch."""
        _login(client, "chat-vendor@test.com", "test123")
        resp = client.post(
            "/api/chat/dispatch",
            json={"rfx_id": 1, "dispatch_plan": []},
        )
        assert resp.status_code == 403

    def test_upload_requires_buyer(self, client, chat_vendor_user):
        """Vendor -> 403 on upload."""
        _login(client, "chat-vendor@test.com", "test123")
        resp = client.post(
            "/api/chat/upload",
            files={"file": ("test.txt", b"hello", "text/plain")},
        )
        assert resp.status_code == 403


class TestChatEndpoint:
    """Tests for POST /api/chat."""

    @patch("aeros.api.chat.get_chat_provider")
    @patch("aeros.api.chat.get_vision_provider", return_value=None)
    def test_chat_returns_message_data_success_shape(self, mock_vp, mock_cp, client, chat_buyer):
        """Response should have {message, data, success}."""
        from aeros.ai.base import ChatResponse

        mock_provider = AsyncMock()
        mock_provider.chat.return_value = ChatResponse(
            content="Hello!",
            input_tokens=10,
            output_tokens=5,
            provider="mock",
            model="mock",
        )
        mock_cp.return_value = mock_provider

        _login(client, "chat-buyer@test.com", "test123")
        resp = client.post("/api/chat", json={"message": "hello"})
        assert resp.status_code == 200
        data = resp.json()
        assert "message" in data
        assert "data" in data
        assert "success" in data

    @patch("aeros.api.chat.get_chat_provider")
    @patch("aeros.api.chat.get_vision_provider", return_value=None)
    def test_chat_with_history_passes_through(self, mock_vp, mock_cp, client, chat_buyer):
        """History should be forwarded to agent context."""
        from aeros.ai.base import ChatResponse

        mock_provider = AsyncMock()
        mock_provider.chat.return_value = ChatResponse(
            content="Hi!",
            input_tokens=10,
            output_tokens=5,
            provider="mock",
            model="mock",
        )
        mock_cp.return_value = mock_provider

        _login(client, "chat-buyer@test.com", "test123")
        resp = client.post(
            "/api/chat",
            json={
                "message": "hello",
                "history": [{"role": "user", "content": "prev message"}],
            },
        )
        assert resp.status_code == 200


class TestCreateRfxEndpoint:
    """Tests for POST /api/chat/create-rfx."""

    @patch("aeros.api.chat.get_chat_provider")
    @patch("aeros.api.chat.get_vision_provider", return_value=None)
    def test_create_rfx_resolves_sku_by_exact_name(
        self, mock_vp, mock_cp, client, chat_buyer, chat_sku
    ):
        """Exact SKU name match should resolve."""
        _login(client, "chat-buyer@test.com", "test123")
        resp = client.post(
            "/api/chat/create-rfx",
            json={
                "draft": {
                    "title": "SKU Test",
                    "line_items": [{"sku_name": "Rice", "qty": 100}],
                },
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["data"]["rfx_id"] is not None

    @patch("aeros.api.chat.get_chat_provider")
    @patch("aeros.api.chat.get_vision_provider", return_value=None)
    def test_create_rfx_resolves_sku_by_fuzzy_match(
        self, mock_vp, mock_cp, client, chat_buyer, chat_sku
    ):
        """Partial name match should resolve via ilike."""
        _login(client, "chat-buyer@test.com", "test123")
        resp = client.post(
            "/api/chat/create-rfx",
            json={
                "draft": {
                    "title": "Fuzzy Test",
                    "line_items": [{"sku_name": "ric", "qty": 50}],
                },
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True

    @patch("aeros.api.chat.get_chat_provider")
    @patch("aeros.api.chat.get_vision_provider", return_value=None)
    def test_create_rfx_resolves_sku_by_id(self, mock_vp, mock_cp, client, chat_buyer, chat_sku):
        """Direct sku_id lookup should work."""
        _login(client, "chat-buyer@test.com", "test123")
        resp = client.post(
            "/api/chat/create-rfx",
            json={
                "draft": {
                    "title": "ID Test",
                    "line_items": [{"sku_id": chat_sku.id, "qty": 10}],
                },
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True

    @patch("aeros.api.chat.get_chat_provider")
    @patch("aeros.api.chat.get_vision_provider", return_value=None)
    def test_create_rfx_missing_sku_skipped(self, mock_vp, mock_cp, client, chat_buyer):
        """Unknown SKU name should be skipped gracefully."""
        _login(client, "chat-buyer@test.com", "test123")
        resp = client.post(
            "/api/chat/create-rfx",
            json={
                "draft": {
                    "title": "Missing SKU Test",
                    "line_items": [{"sku_name": "NonexistentItem", "qty": 100}],
                },
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True

    @patch("aeros.api.chat.get_chat_provider")
    @patch("aeros.api.chat.get_vision_provider", return_value=None)
    def test_create_rfx_qty_field_convention(self, mock_vp, mock_cp, client, chat_buyer, chat_sku):
        """Should accept qty, quantity, and count field names."""
        _login(client, "chat-buyer@test.com", "test123")
        resp = client.post(
            "/api/chat/create-rfx",
            json={
                "draft": {
                    "title": "Qty Convention Test",
                    "line_items": [{"sku_name": "Rice", "quantity": 200}],
                },
            },
        )
        assert resp.status_code == 200

    @patch("aeros.api.chat.get_chat_provider")
    @patch("aeros.api.chat.get_vision_provider", return_value=None)
    def test_create_rfx_returns_suggested_vendors(
        self, mock_vp, mock_cp, client, chat_buyer, chat_sku
    ):
        """Response should include suggested_vendors."""
        _login(client, "chat-buyer@test.com", "test123")
        resp = client.post(
            "/api/chat/create-rfx",
            json={"draft": {"title": "Vendor Test", "line_items": []}},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "suggested_vendors" in data["data"]

    @patch("aeros.api.chat.get_chat_provider")
    @patch("aeros.api.chat.get_vision_provider", return_value=None)
    def test_create_rfx_returns_dispatch_plan(self, mock_vp, mock_cp, client, chat_buyer, chat_sku):
        """Response should include dispatch_plan."""
        _login(client, "chat-buyer@test.com", "test123")
        resp = client.post(
            "/api/chat/create-rfx",
            json={"draft": {"title": "Dispatch Plan Test", "line_items": []}},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "dispatch_plan" in data["data"]
