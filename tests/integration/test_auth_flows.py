"""Integration tests for authentication flows — register, login, access, logout, RBAC, CSRF.

Covers:
1. Register -> Login -> Access protected route -> Logout -> Verify access denied
2. CSRF validation (non-debug mode)
3. Role-based access control (buyer vs vendor vs admin)
4. Token refresh and rotation
"""

import secrets
from datetime import UTC

import pytest

from aeros.models.organization import Organization, OrgType
from aeros.models.user import Role, User, UserStatus
from aeros.models.vendor import Vendor
from aeros.security.jwt import create_refresh_token
from aeros.services.auth_service import hash_password

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def admin_user(session, buyer_org):
    """An admin user for RBAC tests."""
    user = User(
        email="admin-auth@test.com",
        password_hash=hash_password("admin123!"),
        role=Role.ADMIN,
        display_name="Auth Admin",
        org_id=buyer_org.id,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


@pytest.fixture
def vendor_with_profile(session, buyer_org):
    """A vendor user with associated Vendor record."""
    v_org = Organization(name="AuthVendorOrg", type=OrgType.VENDOR)
    session.add(v_org)
    session.commit()
    session.refresh(v_org)

    user = User(
        email="vendor-auth@test.com",
        password_hash=hash_password("vendor123!"),
        role=Role.VENDOR,
        display_name="Auth Vendor",
        org_id=v_org.id,
    )
    session.add(user)
    session.commit()
    session.refresh(user)

    vendor = Vendor(
        owning_buyer_org_id=buyer_org.id,
        vendor_user_id=user.id,
        vendor_org_id=v_org.id,
        name="Auth Vendor Co",
        primary_email="vendor-auth@test.com",
    )
    session.add(vendor)
    session.commit()
    session.refresh(vendor)
    return user, vendor


# ---------------------------------------------------------------------------
# Full Auth Lifecycle
# ---------------------------------------------------------------------------


class TestAuthLifecycle:
    """Register -> Login -> Access -> Logout -> Denied flow."""

    def test_full_auth_lifecycle(self, client):
        """Complete auth lifecycle: register, access, logout, denied."""
        # Step 1: Register
        reg_resp = client.post("/api/auth/register", json={
            "email": "lifecycle@test.com",
            "password": "lifecycle123",
            "display_name": "Lifecycle User",
            "role": "buyer",
        })
        assert reg_resp.status_code == 200
        reg_data = reg_resp.json()
        assert reg_data["email"] == "lifecycle@test.com"
        assert reg_data["role"] == "buyer"
        assert "access_token" in reg_resp.cookies

        # Step 2: Access protected route (cookies set by register)
        me_resp = client.get("/api/auth/me")
        assert me_resp.status_code == 200
        assert me_resp.json()["email"] == "lifecycle@test.com"

        # Step 3: Logout
        logout_resp = client.post("/api/auth/logout")
        assert logout_resp.status_code == 200
        assert logout_resp.json()["ok"] is True

        # Step 4: Access should be denied (cookies deleted)
        # TestClient persists cookies; logout deletes them so subsequent
        # requests should lack valid access_token
        denied_resp = client.get("/api/auth/me")
        assert denied_resp.status_code == 401

    def test_login_after_register(self, client):
        """User should be able to login with credentials after registration."""
        # Register
        client.post("/api/auth/register", json={
            "email": "login-after@test.com",
            "password": "mypassword1",
            "display_name": "Login After",
            "role": "buyer",
        })

        # Logout
        client.post("/api/auth/logout")

        # Login
        login_resp = client.post("/api/auth/login", json={
            "email": "login-after@test.com",
            "password": "mypassword1",
        })
        assert login_resp.status_code == 200
        assert login_resp.json()["email"] == "login-after@test.com"
        assert "access_token" in login_resp.cookies

    def test_register_duplicate_email(self, client, buyer_user):
        """Registering with an existing email should return 409."""
        resp = client.post("/api/auth/register", json={
            "email": "buyer@test.com",
            "password": "some-password1",
            "display_name": "Dup User",
            "role": "buyer",
        })
        assert resp.status_code == 409

    def test_register_invalid_role(self, client):
        """Registering with an invalid role should return 400."""
        resp = client.post("/api/auth/register", json={
            "email": "bad-role@test.com",
            "password": "password123",
            "display_name": "Bad Role",
            "role": "superadmin",
        })
        assert resp.status_code == 400

    def test_register_short_password(self, client):
        """Registering with a too-short password should return 422."""
        resp = client.post("/api/auth/register", json={
            "email": "short-pw@test.com",
            "password": "short",
            "display_name": "Short PW",
            "role": "buyer",
        })
        assert resp.status_code == 422

    def test_login_wrong_password(self, client, buyer_user):
        """Login with wrong password should return 401."""
        resp = client.post("/api/auth/login", json={
            "email": "buyer@test.com",
            "password": "wrong-password",
        })
        assert resp.status_code == 401

    def test_login_nonexistent_user(self, client):
        """Login with nonexistent email should return 401."""
        resp = client.post("/api/auth/login", json={
            "email": "nobody@test.com",
            "password": "password123",
        })
        assert resp.status_code == 401

    def test_access_protected_route_without_auth(self, client):
        """Accessing a protected route without auth should return 401."""
        resp = client.get("/api/buyer/rfx")
        assert resp.status_code == 401

    def test_login_sets_both_cookies(self, client, buyer_user):
        """Login should set both access_token and refresh_token cookies."""
        resp = client.post("/api/auth/login", json={
            "email": "buyer@test.com",
            "password": "test123",
        })
        assert resp.status_code == 200
        assert "access_token" in resp.cookies
        assert "refresh_token" in resp.cookies


# ---------------------------------------------------------------------------
# CSRF Validation
# ---------------------------------------------------------------------------


class TestCSRF:
    """CSRF token validation tests (non-debug mode)."""

    def test_csrf_skipped_in_debug_mode(self, auth_client):
        """In debug mode, CSRF validation should be skipped."""
        # The conftest.py sets settings.debug = True, so POST requests
        # should work without CSRF tokens
        resp = auth_client.post("/api/auth/logout")
        assert resp.status_code == 200

    def test_csrf_enforced_in_production_mode(self, engine):
        """In non-debug mode, POST without CSRF token should be rejected."""
        from fastapi.testclient import TestClient
        from sqlmodel import Session

        from aeros.config import settings
        from aeros.db import get_session
        from aeros.main import app

        # Temporarily switch to production mode
        original_debug = settings.debug
        settings.debug = False

        try:
            def override_get_session():
                with Session(engine) as session:
                    yield session

            app.dependency_overrides[get_session] = override_get_session

            with TestClient(app) as c:
                # POST without CSRF should fail
                resp = c.post("/api/auth/login", json={
                    "email": "test@test.com",
                    "password": "test",
                })
                assert resp.status_code == 403
                assert "CSRF" in resp.json().get("detail", "")
        finally:
            settings.debug = original_debug
            app.dependency_overrides.clear()

    def test_csrf_passes_with_matching_tokens(self, engine, session, buyer_user):
        """In non-debug mode, matching CSRF cookie + header should pass."""
        from fastapi.testclient import TestClient
        from sqlmodel import Session as SQLSession

        from aeros.config import settings
        from aeros.db import get_session
        from aeros.main import app

        original_debug = settings.debug
        settings.debug = False

        try:
            def override_get_session():
                with SQLSession(engine) as s:
                    yield s

            app.dependency_overrides[get_session] = override_get_session

            with TestClient(app) as c:
                csrf_token = secrets.token_urlsafe(32)
                c.cookies.set("aeros_csrf", csrf_token)

                resp = c.post(
                    "/api/auth/login",
                    json={"email": "buyer@test.com", "password": "test123"},
                    headers={"x-csrf-token": csrf_token},
                )
                assert resp.status_code == 200
        finally:
            settings.debug = original_debug
            app.dependency_overrides.clear()

    def test_csrf_fails_with_mismatched_tokens(self, engine):
        """In non-debug mode, mismatched CSRF tokens should fail."""
        from fastapi.testclient import TestClient
        from sqlmodel import Session

        from aeros.config import settings
        from aeros.db import get_session
        from aeros.main import app

        original_debug = settings.debug
        settings.debug = False

        try:
            def override_get_session():
                with Session(engine) as session:
                    yield session

            app.dependency_overrides[get_session] = override_get_session

            with TestClient(app) as c:
                c.cookies.set("aeros_csrf", "token-a")
                resp = c.post(
                    "/api/auth/login",
                    json={"email": "test@test.com", "password": "test"},
                    headers={"x-csrf-token": "token-b"},
                )
                assert resp.status_code == 403
        finally:
            settings.debug = original_debug
            app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Role-Based Access Control
# ---------------------------------------------------------------------------


class TestRBAC:
    """Role-based access control tests — buyer, vendor, admin."""

    def test_buyer_can_access_buyer_routes(self, auth_client):
        """Buyer should access /api/buyer/* routes."""
        resp = auth_client.get("/api/buyer/rfx")
        assert resp.status_code == 200

    def test_buyer_cannot_access_vendor_inbox(self, auth_client):
        """Buyer should not access /api/vendor/inbox."""
        resp = auth_client.get("/api/vendor/inbox")
        assert resp.status_code == 403

    def test_buyer_cannot_access_admin_routes(self, auth_client):
        """Buyer should not access /api/admin/* routes."""
        resp = auth_client.get("/api/admin/stats")
        assert resp.status_code == 403

        resp2 = auth_client.get("/api/admin/users")
        assert resp2.status_code == 403

    def test_vendor_can_access_vendor_routes(self, client, vendor_with_profile):
        """Vendor should access /api/vendor/* routes."""
        user, _ = vendor_with_profile
        client.post("/api/auth/login", json={
            "email": "vendor-auth@test.com",
            "password": "vendor123!",
        })
        resp = client.get("/api/vendor/inbox")
        assert resp.status_code == 200

    def test_vendor_cannot_access_buyer_routes(self, client, vendor_with_profile):
        """Vendor should not access /api/buyer/* routes."""
        user, _ = vendor_with_profile
        client.post("/api/auth/login", json={
            "email": "vendor-auth@test.com",
            "password": "vendor123!",
        })
        resp = client.get("/api/buyer/rfx")
        assert resp.status_code == 403

    def test_vendor_cannot_access_admin_routes(self, client, vendor_with_profile):
        """Vendor should not access /api/admin/* routes."""
        user, _ = vendor_with_profile
        client.post("/api/auth/login", json={
            "email": "vendor-auth@test.com",
            "password": "vendor123!",
        })
        resp = client.get("/api/admin/stats")
        assert resp.status_code == 403

    def test_admin_can_access_admin_routes(self, client, admin_user):
        """Admin should access /api/admin/* routes."""
        client.post("/api/auth/login", json={
            "email": "admin-auth@test.com",
            "password": "admin123!",
        })
        resp = client.get("/api/admin/stats")
        assert resp.status_code == 200

    def test_admin_can_access_buyer_routes(self, client, admin_user):
        """Admin should also access /api/buyer/* routes (admin bypass)."""
        client.post("/api/auth/login", json={
            "email": "admin-auth@test.com",
            "password": "admin123!",
        })
        resp = client.get("/api/buyer/rfx")
        assert resp.status_code == 200

    def test_admin_cannot_access_vendor_routes(self, client, admin_user):
        """Admin should not access /api/vendor/* routes (vendor-only)."""
        client.post("/api/auth/login", json={
            "email": "admin-auth@test.com",
            "password": "admin123!",
        })
        resp = client.get("/api/vendor/inbox")
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Token Mechanics
# ---------------------------------------------------------------------------


class TestTokenMechanics:
    """Tests for JWT token handling edge cases."""

    def test_expired_access_token_rejected(self, client, buyer_user):
        """An expired access token should be rejected."""
        # Create a token with very short TTL that is already expired
        from datetime import datetime, timedelta

        import jwt as pyjwt

        from aeros.config import settings

        payload = {
            "sub": str(buyer_user.id),
            "role": "buyer",
            "type": "access",
            "exp": datetime.now(UTC) - timedelta(minutes=1),
        }
        expired_token = pyjwt.encode(payload, settings.jwt_secret, algorithm="HS256")
        client.cookies.set("access_token", expired_token)

        resp = client.get("/api/auth/me")
        assert resp.status_code == 401

    def test_tampered_token_rejected(self, client, buyer_user):
        """A token signed with the wrong secret should be rejected."""
        from datetime import datetime, timedelta

        import jwt as pyjwt

        payload = {
            "sub": str(buyer_user.id),
            "role": "buyer",
            "type": "access",
            "exp": datetime.now(UTC) + timedelta(minutes=15),
        }
        bad_token = pyjwt.encode(payload, "wrong-secret", algorithm="HS256")
        client.cookies.set("access_token", bad_token)

        resp = client.get("/api/auth/me")
        assert resp.status_code == 401

    def test_refresh_token_cannot_access_routes(self, client, buyer_user):
        """A refresh token should not work as an access token."""
        refresh = create_refresh_token(buyer_user.id)
        client.cookies.set("access_token", refresh)

        resp = client.get("/api/auth/me")
        assert resp.status_code == 401

    def test_refresh_endpoint_with_valid_token(self, client, buyer_user):
        """Refresh endpoint should rotate tokens."""
        # Login first to get refresh token
        login_resp = client.post("/api/auth/login", json={
            "email": "buyer@test.com",
            "password": "test123",
        })
        assert login_resp.status_code == 200

        # Refresh
        refresh_resp = client.post("/api/auth/refresh")
        assert refresh_resp.status_code == 200
        assert refresh_resp.json()["ok"] is True

        # Verify the new access token works
        me_resp = client.get("/api/auth/me")
        assert me_resp.status_code == 200

    def test_suspended_user_cannot_login(self, client, session, buyer_user):
        """A suspended user should not be able to login."""
        buyer_user.status = UserStatus.SUSPENDED
        session.add(buyer_user)
        session.commit()

        resp = client.post("/api/auth/login", json={
            "email": "buyer@test.com",
            "password": "test123",
        })
        assert resp.status_code == 401

    def test_register_as_vendor_creates_vendor_role(self, client):
        """Registering with role=vendor should create a vendor-role user."""
        resp = client.post("/api/auth/register", json={
            "email": "new-vendor@test.com",
            "password": "vendorpass1",
            "display_name": "New Vendor",
            "role": "vendor",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["role"] == "vendor"
        assert data["email"] == "new-vendor@test.com"


# ---------------------------------------------------------------------------
# Health Endpoint (Public)
# ---------------------------------------------------------------------------


class TestPublicEndpoints:
    """Tests for publicly accessible endpoints."""

    def test_health_endpoint_no_auth(self, client):
        """GET /health should be accessible without authentication."""
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["service"] == "aeros"
