import time
from collections import defaultdict

from fastapi import HTTPException, Request
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

from aeros.config import settings


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: object, requests_per_minute: int = 60, burst: int = 10) -> None:
        super().__init__(app)  # type: ignore[arg-type]
        self.rpm = requests_per_minute
        self.burst = burst
        self._buckets: dict[str, list[float]] = defaultdict(list)

    def _get_client_key(self, request: Request) -> str:
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if settings.debug:
            return await call_next(request)

        if request.url.path in ("/health", "/docs", "/openapi.json"):
            return await call_next(request)

        key = self._get_client_key(request)
        now = time.monotonic()
        window = 60.0

        self._buckets[key] = [t for t in self._buckets[key] if now - t < window]

        if len(self._buckets[key]) >= self.rpm:
            raise HTTPException(429, "Rate limit exceeded")

        self._buckets[key].append(now)
        response = await call_next(request)
        response.headers["X-RateLimit-Remaining"] = str(self.rpm - len(self._buckets[key]))
        return response
