import secrets

from fastapi import HTTPException, Request
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

from aeros.config import settings

CSRF_COOKIE = "aeros_csrf"
CSRF_HEADER = "x-csrf-token"
SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}


class CSRFMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        secure = not settings.debug

        # Skip CSRF validation in debug/test mode
        if settings.debug:
            response = await call_next(request)
            if CSRF_COOKIE not in request.cookies:
                token = secrets.token_urlsafe(32)
                response.set_cookie(
                    CSRF_COOKIE, token, httponly=False, samesite="lax", secure=secure
                )
            return response

        if request.method in SAFE_METHODS:
            response = await call_next(request)
            if CSRF_COOKIE not in request.cookies:
                token = secrets.token_urlsafe(32)
                response.set_cookie(
                    CSRF_COOKIE, token, httponly=False, samesite="lax", secure=secure
                )
            return response

        cookie_token = request.cookies.get(CSRF_COOKIE)
        header_token = request.headers.get(CSRF_HEADER)

        if not cookie_token or not header_token or cookie_token != header_token:
            raise HTTPException(403, "CSRF validation failed")

        response = await call_next(request)
        return response
