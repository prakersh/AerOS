"""Tests for the /api/auth/refresh endpoint."""

from aeros.security.jwt import create_access_token


class TestRefreshEndpoint:
    def test_refresh_happy_path(self, auth_client, buyer_user):
        """Valid refresh token should return new access token."""
        resp = auth_client.post("/api/auth/refresh")
        assert resp.status_code == 200
        assert resp.json()["ok"] is True
        # Verify the new access token works
        resp2 = auth_client.get("/api/auth/me")
        assert resp2.status_code == 200

    def test_refresh_no_token(self, client):
        """Missing refresh token should return 401."""
        resp = client.post("/api/auth/refresh")
        assert resp.status_code == 401

    def test_refresh_with_access_token_as_refresh(self, client, buyer_user):
        """An access token used as refresh token should be rejected."""
        token = create_access_token(buyer_user.id, "buyer")
        client.cookies.set("refresh_token", token)
        resp = client.post("/api/auth/refresh")
        assert resp.status_code == 401
        detail = resp.json().get("detail", "")
        assert "token type" in detail.lower(), f"Expected 'token type' in detail, got: {detail}"

    def test_refresh_suspended_user(self, client, session, buyer_user):
        """Refresh for a suspended user should return 403."""
        from aeros.models.user import UserStatus

        # First login to get refresh token
        resp = client.post(
            "/api/auth/login",
            json={"email": "buyer@test.com", "password": "test123"},
        )
        assert resp.status_code == 200

        # Suspend the user
        buyer_user.status = UserStatus.SUSPENDED
        session.add(buyer_user)
        session.commit()

        # Try refresh
        resp2 = client.post("/api/auth/refresh")
        assert resp2.status_code == 403

    def test_refresh_invalid_token(self, client):
        """Garbage refresh token should return 401."""
        client.cookies.set("refresh_token", "not.a.valid.jwt.token")
        resp = client.post("/api/auth/refresh")
        assert resp.status_code == 401

    def test_refresh_rotates_token(self, auth_client):
        """Refresh should issue a new refresh token (rotation)."""
        resp = auth_client.post("/api/auth/refresh")
        assert resp.status_code == 200
        assert resp.json()["ok"] is True
        # The response should set new cookies via Set-Cookie headers.
        # httpx / TestClient may combine multiple Set-Cookie values into a
        # single comma-separated header, so we collect all raw values and
        # look for cookie names inside them.
        raw_cookies = [v for k, v in resp.headers.items() if k.lower() == "set-cookie"]
        combined = " ".join(raw_cookies)
        assert "access_token=" in combined, (
            f"Expected access_token cookie in Set-Cookie, got: {combined}"
        )
        assert "refresh_token=" in combined, (
            f"Expected refresh_token cookie in Set-Cookie, got: {combined}"
        )
