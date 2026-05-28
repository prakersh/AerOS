"""Tests for security middleware — CSRF and rate limiting."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.requests import Request
from starlette.responses import Response

# ---- CSRF tests ----


class TestCSRFMiddleware:
    """Tests for CSRF token validation by calling dispatch directly."""

    def _build_request(self, method="GET", cookies=None, headers=None) -> Request:
        """Build a minimal ASGI scope request."""
        scope = {
            "type": "http",
            "method": method,
            "path": "/test",
            "query_string": b"",
            "headers": [],
        }
        if headers:
            scope["headers"] = [(k.lower().encode(), v.encode()) for k, v in headers.items()]
        # Starlette reads cookies from the 'cookie' header
        if cookies:
            cookie_str = "; ".join(f"{k}={v}" for k, v in cookies.items())
            scope["headers"].append((b"cookie", cookie_str.encode()))
        return Request(scope)

    def test_safe_method_sets_csrf_cookie(self):
        """GET requests should set a CSRF cookie on the response."""
        from aeros.security.csrf import CSRFMiddleware

        app = FastAPI()
        app.add_middleware(CSRFMiddleware)

        @app.get("/test")
        def handler():
            return {"ok": True}

        with TestClient(app) as client:
            resp = client.get("/test")
            assert resp.status_code == 200
            assert "aeros_csrf" in resp.cookies

    def test_get_succeeds_without_csrf(self):
        """GET should succeed without any CSRF tokens."""
        from aeros.security.csrf import CSRFMiddleware

        app = FastAPI()
        app.add_middleware(CSRFMiddleware)

        @app.get("/test")
        def handler():
            return {"ok": True}

        with TestClient(app) as client:
            resp = client.get("/test")
            assert resp.status_code == 200

    def test_post_fails_without_tokens_via_dispatch(self):
        """POST without CSRF tokens should return 403."""
        from aeros.security.csrf import CSRFMiddleware

        middleware = CSRFMiddleware(app=None)
        request = self._build_request(method="POST")

        call_next = AsyncMock()

        import asyncio

        with patch("aeros.security.csrf.settings") as mock_settings:
            mock_settings.debug = False
            result = asyncio.run(middleware.dispatch(request, call_next))
        assert result.status_code == 403
        call_next.assert_not_called()

    def test_post_fails_with_mismatched_tokens_via_dispatch(self):
        """POST with mismatched cookie/header should return 403."""
        from aeros.security.csrf import CSRFMiddleware

        middleware = CSRFMiddleware(app=None)
        request = self._build_request(
            method="POST",
            cookies={"aeros_csrf": "token-a"},
            headers={"x-csrf-token": "token-b"},
        )
        call_next = AsyncMock()

        import asyncio

        with patch("aeros.security.csrf.settings") as mock_settings:
            mock_settings.debug = False
            result = asyncio.run(middleware.dispatch(request, call_next))
        assert result.status_code == 403

    def test_post_succeeds_with_matching_tokens_via_dispatch(self):
        """POST with matching cookie and header should succeed."""
        from aeros.security.csrf import CSRFMiddleware

        middleware = CSRFMiddleware(app=None)
        request = self._build_request(
            method="POST",
            cookies={"aeros_csrf": "valid-token-123"},
            headers={"x-csrf-token": "valid-token-123"},
        )
        expected_response = Response(content="ok", status_code=200)
        call_next = AsyncMock(return_value=expected_response)

        import asyncio

        with patch("aeros.security.csrf.settings") as mock_settings:
            mock_settings.debug = False
            result = asyncio.run(middleware.dispatch(request, call_next))
        assert result.status_code == 200
        call_next.assert_called_once()

    def test_post_fails_with_only_cookie_via_dispatch(self):
        """POST with only cookie but no header should return 403."""
        from aeros.security.csrf import CSRFMiddleware

        middleware = CSRFMiddleware(app=None)
        request = self._build_request(method="POST", cookies={"aeros_csrf": "token-only"})
        call_next = AsyncMock()

        import asyncio

        with patch("aeros.security.csrf.settings") as mock_settings:
            mock_settings.debug = False
            result = asyncio.run(middleware.dispatch(request, call_next))
        assert result.status_code == 403

    def test_post_fails_with_only_header_via_dispatch(self):
        """POST with only header but no cookie should return 403."""
        from aeros.security.csrf import CSRFMiddleware

        middleware = CSRFMiddleware(app=None)
        request = self._build_request(method="POST", headers={"x-csrf-token": "token-only"})
        call_next = AsyncMock()

        import asyncio

        with patch("aeros.security.csrf.settings") as mock_settings:
            mock_settings.debug = False
            result = asyncio.run(middleware.dispatch(request, call_next))
        assert result.status_code == 403

    def test_safe_method_does_not_set_cookie_if_already_present(self):
        """GET with existing CSRF cookie should not set a new one."""
        from aeros.security.csrf import CSRFMiddleware

        middleware = CSRFMiddleware(app=None)
        request = self._build_request(method="GET", cookies={"aeros_csrf": "existing-token"})
        mock_response = MagicMock()
        mock_response.set_cookie = MagicMock()
        call_next = AsyncMock(return_value=mock_response)

        import asyncio

        asyncio.run(middleware.dispatch(request, call_next))
        mock_response.set_cookie.assert_not_called()


# ---- Rate limit tests ----


class TestRateLimitMiddleware:
    """Tests for rate limiting middleware."""

    def _make_rate_limit_app(self, rpm=5, burst=2):
        """Create a minimal app with rate limit middleware."""
        from aeros.security.rate_limit import RateLimitMiddleware

        app = FastAPI()
        app.add_middleware(RateLimitMiddleware, requests_per_minute=rpm, burst=burst)

        @app.get("/test")
        def test_endpoint():
            return {"ok": True}

        @app.get("/health")
        def health():
            return {"status": "ok"}

        return app

    def test_health_endpoint_bypasses_rate_limit(self):
        """/health should bypass rate limiting."""
        app = self._make_rate_limit_app(rpm=1)
        with TestClient(app) as client:
            for _ in range(10):
                resp = client.get("/health")
                assert resp.status_code == 200

    def test_normal_requests_succeed(self):
        """Normal requests within limit should succeed."""
        app = self._make_rate_limit_app(rpm=10)
        with TestClient(app) as client:
            resp = client.get("/test")
            assert resp.status_code == 200

    def test_rate_limit_exceeded_via_dispatch(self):
        """Should raise 429 when rate limit is exceeded."""
        from aeros.security.rate_limit import RateLimitMiddleware

        with patch("aeros.security.rate_limit.settings") as mock_settings:
            mock_settings.debug = False
            middleware = RateLimitMiddleware(app=None, requests_per_minute=2)

            request = MagicMock()
            request.url.path = "/test"
            request.headers = {}
            request.client.host = "127.0.0.1"

            call_next = AsyncMock(return_value=Response(content="ok"))

            import asyncio

            # First two requests should succeed
            asyncio.run(middleware.dispatch(request, call_next))
            asyncio.run(middleware.dispatch(request, call_next))

            # Third request should be rate limited
            with pytest.raises(Exception) as exc_info:
                asyncio.run(middleware.dispatch(request, call_next))
            assert exc_info.value.status_code == 429

    def test_rate_limit_resets_after_window(self):
        """Rate limit should reset after the time window expires."""
        from aeros.security.rate_limit import RateLimitMiddleware

        with patch("aeros.security.rate_limit.settings") as mock_settings:
            mock_settings.debug = False
            middleware = RateLimitMiddleware(app=None, requests_per_minute=2)

            request = MagicMock()
            request.url.path = "/test"
            request.headers = {}
            request.client.host = "127.0.0.1"

            call_next = AsyncMock(return_value=Response(content="ok"))

            import asyncio

            # Exhaust limit
            asyncio.run(middleware.dispatch(request, call_next))
            asyncio.run(middleware.dispatch(request, call_next))

            # Third should fail
            with pytest.raises(Exception):  # noqa: B017
                asyncio.run(middleware.dispatch(request, call_next))

            # Clear the bucket by advancing time
            middleware._buckets["127.0.0.1"] = []

            # Should succeed again
            result = asyncio.run(middleware.dispatch(request, call_next))
            assert result.status_code == 200

    def test_rate_limit_response_has_remaining_header(self):
        """Successful responses should include X-RateLimit-Remaining header."""
        from aeros.security.rate_limit import RateLimitMiddleware

        with patch("aeros.security.rate_limit.settings") as mock_settings:
            mock_settings.debug = False
            middleware = RateLimitMiddleware(app=None, requests_per_minute=10)

            request = MagicMock()
            request.url.path = "/test"
            request.headers = {}
            request.client.host = "127.0.0.1"

            response = Response(content="ok")
            call_next = AsyncMock(return_value=response)

            import asyncio

            result = asyncio.run(middleware.dispatch(request, call_next))
            assert "X-RateLimit-Remaining" in result.headers

    def test_x_forwarded_for_used_as_client_key(self):
        """Should use X-Forwarded-For header for client identification."""
        from aeros.security.rate_limit import RateLimitMiddleware

        with patch("aeros.security.rate_limit.settings") as mock_settings:
            mock_settings.debug = False
            middleware = RateLimitMiddleware(app=None, requests_per_minute=2)

            def make_request(forwarded_for):
                req = MagicMock()
                req.url.path = "/test"
                req.headers = {"x-forwarded-for": forwarded_for}
                req.client.host = "127.0.0.1"
                return req

            call_next = AsyncMock(return_value=Response(content="ok"))

            import asyncio

            # Two requests from IP 1
            asyncio.run(middleware.dispatch(make_request("10.0.0.1"), call_next))
            asyncio.run(middleware.dispatch(make_request("10.0.0.1"), call_next))

            # Third from same IP should fail
            with pytest.raises(Exception) as exc_info:
                asyncio.run(middleware.dispatch(make_request("10.0.0.1"), call_next))
            assert exc_info.value.status_code == 429

            # Different IP should succeed
            result = asyncio.run(middleware.dispatch(make_request("10.0.0.2"), call_next))
            assert result.status_code == 200

    def test_docs_endpoint_bypasses_rate_limit(self):
        """/docs and /openapi.json should bypass rate limiting."""
        from aeros.security.rate_limit import RateLimitMiddleware

        with patch("aeros.security.rate_limit.settings") as mock_settings:
            mock_settings.debug = False
            middleware = RateLimitMiddleware(app=None, requests_per_minute=1)

            for path in ("/docs", "/openapi.json"):
                request = MagicMock()
                request.url.path = path
                request.headers = {}
                request.client.host = "127.0.0.1"
                call_next = AsyncMock(return_value=Response(content="ok"))

                import asyncio

                # Should never be rate limited
                for _ in range(5):
                    result = asyncio.run(middleware.dispatch(request, call_next))
                    assert result.status_code == 200
