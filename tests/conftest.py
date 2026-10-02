"""Shared fixtures: a throwaway local database and an in-process API client.

The environment is pinned *before* anything from ``app`` is imported.
``app.core.config`` builds its settings at import time and falls back to
``.env`` for anything unset, and ``.env`` points at the AWS database.
"""

import os
from collections.abc import AsyncGenerator

TEST_DATABASE = "habit_tracker_test"
INTERNAL_API_KEY = "test-only-internal-api-key"

os.environ.update(
    {
        "APP_ENV": "local",
        "POSTGRES_HOST": "localhost",
        "POSTGRES_PORT": "5432",
        "POSTGRES_USER": "postgres",
        "POSTGRES_PASSWORD": "postgres",
        "POSTGRES_DB": TEST_DATABASE,
        "INTERNAL_API_KEY": INTERNAL_API_KEY,
        "JWT_SECRET": "test-only-jwt-secret-not-used-anywhere-else",
        # Shaped like a real token because aiogram validates the format when
        # ``bot.webhook`` builds its Bot at import time. It is never used.
        "TELEGRAM_BOT_TOKEN": "123456:TEST-TOKEN-aaaaaaaaaaaaaaaaaaaaaaaaa",
        "CORS_ORIGINS": "http://localhost:5173",
    }
)

import asyncpg  # noqa: E402
import pytest  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402
from sqlalchemy import text  # noqa: E402

import app.models  # noqa: E402, F401  (registers every table on Base.metadata)
from app.core.config import settings  # noqa: E402
from app.db.base import Base  # noqa: E402
from app.db.session import engine  # noqa: E402
from app.main import app as fastapi_app  # noqa: E402

# Every test wipes these tables, so refuse to run against anything that is
# not the local throwaway database.
if settings.postgres_host not in {"localhost", "127.0.0.1"} or settings.postgres_db != TEST_DATABASE:
    raise RuntimeError(
        f"Refusing to run tests against {settings.postgres_host}/{settings.postgres_db}."
    )


@pytest.fixture(scope="session", autouse=True)
async def _database() -> AsyncGenerator[None, None]:
    """Create the test database if needed and rebuild its tables from the models."""
    admin = await asyncpg.connect(
        host=settings.postgres_host,
        port=settings.postgres_port,
        user=settings.postgres_user,
        password=settings.postgres_password,
        database="postgres",
    )
    try:
        exists = await admin.fetchval(
            "SELECT 1 FROM pg_database WHERE datname = $1", TEST_DATABASE
        )
        if not exists:
            await admin.execute(f'CREATE DATABASE "{TEST_DATABASE}"')
    finally:
        await admin.close()

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)
        await connection.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


@pytest.fixture(autouse=True)
async def _clean_tables(_database: None) -> None:
    """Start every test from empty tables and ids counting from 1."""
    tables = ", ".join(f'"{table.name}"' for table in Base.metadata.sorted_tables)
    async with engine.begin() as connection:
        await connection.execute(text(f"TRUNCATE {tables} RESTART IDENTITY CASCADE"))


def _headers(telegram_id: int) -> dict[str, str]:
    """The bot's header scheme: a tenant id vouched for by the shared secret."""
    return {"X-Telegram-Id": str(telegram_id), "X-Internal-Api-Key": INTERNAL_API_KEY}


async def _client(telegram_id: int) -> AsyncGenerator[AsyncClient, None]:
    transport = ASGITransport(app=fastapi_app)
    async with AsyncClient(
        transport=transport,
        base_url="http://test",
        headers=_headers(telegram_id),
    ) as client:
        yield client


@pytest.fixture
async def alice() -> AsyncGenerator[AsyncClient, None]:
    """An API client authenticated as the first tenant."""
    async for client in _client(1001):
        yield client


@pytest.fixture
async def bob() -> AsyncGenerator[AsyncClient, None]:
    """An API client authenticated as a second, unrelated tenant."""
    async for client in _client(2002):
        yield client


async def make_activity(client: AsyncClient, name: str = "Running", unit: str = "km") -> int:
    """Create an activity through the API and return its id."""
    response = await client.post("/activities", json={"name": name, "unit": unit})
    assert response.status_code == 201, response.text
    return int(response.json()["id"])


async def make_log(client: AsyncClient, activity_id: int, amount: str = "5.00") -> int:
    """Create a journal entry through the API and return its id."""
    response = await client.post("/logs", json={"activity_id": activity_id, "amount": amount})
    assert response.status_code == 201, response.text
    return int(response.json()["id"])
