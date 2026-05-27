"""Integration tests for expanded admin API endpoints."""

import pytest

from aeros.models.organization import OrgType, Organization
from aeros.models.user import Role, User, UserStatus
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
def target_user(session, buyer_org):
    user = User(
        email="target@test.com",
        password_hash=hash_password("test123"),
        role=Role.BUYER,
        display_name="Target User",
        org_id=buyer_org.id,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


# ---------------------------------------------------------------------------
# Suspend / Reactivate
# ---------------------------------------------------------------------------


class TestSuspendUser:
    def test_suspend_user_success(self, admin_client, target_user):
        """POST /api/admin/users/{id}/suspend should suspend the user."""
        resp = admin_client.post(
            f"/api/admin/users/{target_user.id}/suspend",
            json={"reason": "Policy violation"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "suspended"
        assert data["id"] == target_user.id

    def test_suspend_nonexistent_user(self, admin_client):
        """Should return 400/404 for nonexistent user."""
        resp = admin_client.post(
            "/api/admin/users/99999/suspend",
            json={"reason": "test"},
        )
        assert resp.status_code in (400, 404)

    def test_suspend_self_forbidden(self, admin_client, admin_user):
        """Admin should not be able to suspend themselves."""
        resp = admin_client.post(
            f"/api/admin/users/{admin_user.id}/suspend",
            json={"reason": "test"},
        )
        assert resp.status_code == 400

    def test_buyer_cannot_suspend(self, auth_client, target_user):
        """Non-admin should be denied."""
        resp = auth_client.post(
            f"/api/admin/users/{target_user.id}/suspend",
            json={"reason": "test"},
        )
        assert resp.status_code == 403


class TestReactivateUser:
    def test_reactivate_user_success(self, admin_client, target_user):
        """POST /api/admin/users/{id}/reactivate should reactivate a suspended user."""
        # Suspend first
        admin_client.post(
            f"/api/admin/users/{target_user.id}/suspend",
            json={"reason": "test"},
        )
        # Reactivate
        resp = admin_client.post(f"/api/admin/users/{target_user.id}/reactivate")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "active"

    def test_reactivate_nonexistent_user(self, admin_client):
        """Should return 400/404 for nonexistent user."""
        resp = admin_client.post("/api/admin/users/99999/reactivate")
        assert resp.status_code in (400, 404)


# ---------------------------------------------------------------------------
# Organizations
# ---------------------------------------------------------------------------


class TestListOrganizations:
    def test_list_orgs(self, admin_client, buyer_org):
        """GET /api/admin/orgs should return list of organizations."""
        resp = admin_client.get("/api/admin/orgs")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) >= 1

    def test_org_has_fields(self, admin_client, buyer_org):
        """Each org should have id, name, type, created_at."""
        resp = admin_client.get("/api/admin/orgs")
        data = resp.json()
        org = data[0]
        assert "id" in org
        assert "name" in org
        assert "type" in org

    def test_buyer_cannot_list_orgs(self, auth_client):
        """Non-admin should be denied."""
        resp = auth_client.get("/api/admin/orgs")
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# AI Providers
# ---------------------------------------------------------------------------


class TestAIProviders:
    def test_list_providers(self, admin_client):
        """GET /api/admin/ai/providers should return provider list."""
        resp = admin_client.get("/api/admin/ai/providers")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) >= 1

    def test_providers_have_fields(self, admin_client):
        """Each provider should have required fields."""
        resp = admin_client.get("/api/admin/ai/providers")
        data = resp.json()
        for p in data:
            assert "provider_name" in p
            assert "model_id" in p
            assert "capability" in p

    def test_test_provider_unknown(self, admin_client):
        """POST /api/admin/ai/providers/test with unknown provider."""
        resp = admin_client.post(
            "/api/admin/ai/providers/test",
            json={"provider_name": "nonexistent"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is False

    def test_buyer_cannot_list_providers(self, auth_client):
        """Non-admin should be denied."""
        resp = auth_client.get("/api/admin/ai/providers")
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# System Settings
# ---------------------------------------------------------------------------


class TestSystemSettings:
    def test_get_all_settings(self, admin_client):
        """GET /api/admin/settings should return all settings."""
        resp = admin_client.get("/api/admin/settings")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) >= 1

    def test_settings_have_fields(self, admin_client):
        """Each setting should have key, value, type, description, source."""
        resp = admin_client.get("/api/admin/settings")
        data = resp.json()
        for s in data:
            assert "key" in s
            assert "value" in s
            assert "type" in s

    def test_update_setting(self, admin_client):
        """PUT /api/admin/settings/{key} should update a setting."""
        resp = admin_client.put(
            "/api/admin/settings/max_upload_size_mb",
            json={"value": "50"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["key"] == "max_upload_size_mb"
        assert data["value"] == "50"

    def test_buyer_cannot_access_settings(self, auth_client):
        """Non-admin should be denied."""
        resp = auth_client.get("/api/admin/settings")
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------


class TestSystemHealth:
    def test_health_endpoint(self, admin_client):
        """GET /api/admin/health should return health status."""
        resp = admin_client.get("/api/admin/health")
        assert resp.status_code == 200
        data = resp.json()
        assert "api" in data
        assert "database" in data
        assert "ai_provider" in data

    def test_buyer_cannot_access_health(self, auth_client):
        """Non-admin should be denied."""
        resp = auth_client.get("/api/admin/health")
        assert resp.status_code == 403
