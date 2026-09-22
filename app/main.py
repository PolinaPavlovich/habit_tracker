"""FastAPI application entrypoint."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from mangum import Mangum

from app.api.router import api_router
from app.core.config import settings
from app.db.session import engine

from bot.webhook import router as telegram_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Dispose of the connection pool when the application shuts down."""
    yield
    await engine.dispose()


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    lifespan=lifespan,
)

# The SPA is served from Vercel, a different origin, and it sends an
# Authorization header — a non-simple header, so every request preflights.
# Without this middleware the browser blocks each one before it reaches a route.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

app.include_router(api_router)
app.include_router(telegram_router)


@app.get("/health", tags=["system"], summary="Liveness probe")
async def health() -> dict[str, str]:
    """Return a static payload used by the container healthcheck."""
    return {"status": "ok", "env": settings.app_env}

handler = Mangum(app)
