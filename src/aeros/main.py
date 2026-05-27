from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from aeros.config import settings
from aeros.security.csrf import CSRFMiddleware
from aeros.security.rate_limit import RateLimitMiddleware
from aeros.api import auth as auth_router
from aeros.api import buyer as buyer_router
from aeros.api import vendor as vendor_router
from aeros.api import chat as chat_router
from aeros.api import admin as admin_router
from aeros.api import po as po_router
from aeros.api import observability as observability_router
from aeros.api import inbound_telegram as telegram_router

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    if not settings.debug and (settings.jwt_secret == "change-me" or settings.hmac_secret == "change-me"):
        raise RuntimeError(
            "AEROS_JWT_SECRET and AEROS_HMAC_SECRET must be set — "
            "refusing to start with default secrets."
        )
    logger.info("aeros.startup", port=settings.port)
    yield
    logger.info("aeros.shutdown")


app = FastAPI(
    title="AEROS",
    description="AI Procurement OS",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(RateLimitMiddleware, requests_per_minute=120, burst=20)
app.add_middleware(CSRFMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allowed_origins.split(","),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "x-csrf-token"],
)

app.include_router(auth_router.router)
app.include_router(buyer_router.router)
app.include_router(vendor_router.router)
app.include_router(chat_router.router)
app.include_router(admin_router.router)
app.include_router(po_router.router)
app.include_router(observability_router.router)
app.include_router(telegram_router.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "aeros"}
