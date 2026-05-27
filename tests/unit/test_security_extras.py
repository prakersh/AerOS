"""Tests for security headers, HMAC verification, auth_context, and db_scope."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from aeros.models.user import Role
from aeros.security.auth_context import AuthContext

# ---- Security headers middleware ----


class TestSecurityHeaders:
    async def test_headers_added_to_response(self):
        """Security headers should be added to every response."""
        from starlette.requests import Request
        from starlette.responses import Response

        from aeros.security.headers import SECURITY_HEADERS, SecurityHeadersMiddleware

        middleware = SecurityHeadersMiddleware(app=None)

        scope = {
            "type": "http",
            "method": "GET",
            "path": "/test",
            "query_string": b"",
            "headers": [],
        }
        request = Request(scope)
        call_next = AsyncMock(return_value=Response(content="ok"))

        result = await middleware.dispatch(request, call_next)

        for header, value in SECURITY_HEADERS.items():
            assert result.headers[header] == value

    async def test_security_headers_dict_content(self):
        """SECURITY_HEADERS should contain expected entries."""
        from aeros.security.headers import SECURITY_HEADERS

        assert "X-Content-Type-Options" in SECURITY_HEADERS
        assert "X-Frame-Options" in SECURITY_HEADERS
        assert SECURITY_HEADERS["X-Frame-Options"] == "DENY"


# ---- HMAC verification ----


class TestHMACVerification:
    def test_no_dot_returns_none(self):
        """Token without a dot separator should return None."""
        from aeros.security.hmac import verify_correlation_token
        assert verify_correlation_token("noseparator") is None


# ---- AuthContext / require_role ----


class TestAuthContext:
    def test_auth_context_creation(self):
        ctx = AuthContext(user_id=1, role=Role.BUYER, org_id=10)
        assert ctx.user_id == 1
        assert ctx.role == Role.BUYER
        assert ctx.org_id == 10

    def test_auth_context_defaults(self):
        ctx = AuthContext(user_id=1, role=Role.VENDOR)
        assert ctx.org_id is None


# ---- db_scope ----


class TestDbScope:
    def test_admin_sees_everything(self):
        """Admin should get the statement back unchanged."""
        from aeros.db_scope import for_user

        caller = AuthContext(user_id=1, role=Role.ADMIN, org_id=1)
        mock_stmt = MagicMock()
        result = for_user(caller, mock_stmt)
        assert result is mock_stmt

    def test_buyer_without_buyer_org_field(self):
        """Buyer without buyer_org_field should get statement back unchanged."""
        from aeros.db_scope import for_user

        caller = AuthContext(user_id=1, role=Role.BUYER, org_id=10)
        mock_stmt = MagicMock()
        result = for_user(caller, mock_stmt)
        assert result is mock_stmt

    def test_vendor_without_user_field(self):
        """Vendor without user_field should get statement back unchanged."""
        from aeros.db_scope import for_user

        caller = AuthContext(user_id=5, role=Role.VENDOR, org_id=20)
        mock_stmt = MagicMock()
        result = for_user(caller, mock_stmt)
        assert result is mock_stmt

    def test_unknown_role_raises(self):
        """Unknown role should raise MissingScopeError."""
        from aeros.db_scope import MissingScopeError, for_user

        caller = AuthContext(user_id=1, role="unknown_role")
        mock_stmt = MagicMock()
        with pytest.raises(MissingScopeError):
            for_user(caller, mock_stmt)

    def test_admin_role_string(self):
        """Admin role as string should also pass through."""
        from aeros.db_scope import for_user

        caller = AuthContext(user_id=1, role="admin")
        mock_stmt = MagicMock()
        result = for_user(caller, mock_stmt)
        assert result is mock_stmt
