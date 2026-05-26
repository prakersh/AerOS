from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from aeros.config import settings
from aeros.api import auth as auth_router
from aeros.api import buyer as buyer_router
from aeros.api import vendor as vendor_router
from aeros.api import chat as chat_router

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    logger.info("aeros.startup", port=settings.port)
    yield
    logger.info("aeros.shutdown")


app = FastAPI(
    title="AEROS",
    description="AI Procurement OS",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allowed_origins.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router.router)
app.include_router(buyer_router.router)
app.include_router(vendor_router.router)
app.include_router(chat_router.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "aeros"}
