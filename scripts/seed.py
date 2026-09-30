"""Fill the local database with a mock user and 30 days of journal entries.

Run through ``bin/dev``, or ``python -m scripts.seed`` with the same exports.
Also mints a login token for the mock user into ``frontend/.env.development.local``
so the dev frontend skips the QR screen.
"""

import asyncio
import random
import sys
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

from sqlalchemy import delete

from app.core.config import settings
from app.core.security import create_tv_token
from app.db.session import AsyncSessionLocal, engine
from app.models import Activity, Log, User

MOCK_TELEGRAM_ID = 999_000_001
MOCK_USERNAME = "dev_user"
DAYS = 30
LOCAL_HOSTS = frozenset({"localhost", "127.0.0.1"})
DEV_SECRET_PREFIX = "local-dev-only"
FRONTEND_ENV_FILE = Path(__file__).resolve().parent.parent / "frontend" / ".env.development.local"


@dataclass(frozen=True, slots=True)
class HabitSpec:
    name: str
    unit: str
    daily_probability: float
    min_amount: Decimal
    max_amount: Decimal
    whole_numbers: bool


HABITS: tuple[HabitSpec, ...] = (
    HabitSpec("Running", "km", 0.45, Decimal("3"), Decimal("10"), whole_numbers=False),
    HabitSpec("Push-ups", "reps", 0.9, Decimal("20"), Decimal("60"), whole_numbers=True),
    HabitSpec("Reading", "pages", 0.7, Decimal("10"), Decimal("50"), whole_numbers=True),
)


def refuse_unless_local() -> None:
    """Exit before touching anything unless every setting says local.

    ``app_env`` defaults to "local", so it cannot be trusted alone: the host
    check is what stops this running against the AWS database in ``.env``, and
    the secret check stops a dev token being signed with the production key.
    """
    problems: list[str] = []
    if settings.app_env != "local":
        problems.append(f"APP_ENV is {settings.app_env!r}, expected 'local'")
    if settings.postgres_host not in LOCAL_HOSTS:
        problems.append(f"POSTGRES_HOST is {settings.postgres_host!r}, expected localhost")
    if not settings.jwt_secret.startswith(DEV_SECRET_PREFIX):
        problems.append(f"JWT_SECRET does not start with {DEV_SECRET_PREFIX!r}")
    if problems:
        print("Refusing to seed:\n  - " + "\n  - ".join(problems), file=sys.stderr)
        raise SystemExit(1)


def random_amount(rng: random.Random, spec: HabitSpec) -> Decimal:
    if spec.whole_numbers:
        return Decimal(rng.randint(int(spec.min_amount), int(spec.max_amount)))
    value = rng.uniform(float(spec.min_amount), float(spec.max_amount))
    return Decimal(str(value)).quantize(Decimal("0.01"))


async def seed() -> tuple[int, int]:
    """Replace the mock user's data. Returns ``(user_id, log_count)``."""
    rng = random.Random(42)
    today = date.today()

    async with AsyncSessionLocal() as session, session.begin():
        # ON DELETE CASCADE removes the user's activities, logs and QR sessions.
        await session.execute(delete(User).where(User.telegram_id == MOCK_TELEGRAM_ID))

        user = User(telegram_id=MOCK_TELEGRAM_ID, username=MOCK_USERNAME)
        session.add(user)
        await session.flush()

        logs: list[Log] = []
        for spec in HABITS:
            activity = Activity(user_id=user.id, name=spec.name, unit=spec.unit)
            session.add(activity)
            await session.flush()
            for offset in range(DAYS):
                if rng.random() < spec.daily_probability:
                    logs.append(
                        Log(
                            activity_id=activity.id,
                            amount=random_amount(rng, spec),
                            date=today - timedelta(days=offset),
                        )
                    )
        session.add_all(logs)
        return user.id, len(logs)


def write_frontend_token(user_id: int) -> None:
    token = create_tv_token(
        user_id=user_id,
        secret=settings.jwt_secret,
        ttl_seconds=settings.jwt_ttl_seconds,
    )
    FRONTEND_ENV_FILE.write_text(
        "# Written by scripts/seed.py. Gitignored; read only by `vite` in dev mode.\n"
        f"VITE_DEV_TOKEN={token}\n"
    )


async def main() -> None:
    refuse_unless_local()
    try:
        user_id, log_count = await seed()
    finally:
        await engine.dispose()
    write_frontend_token(user_id)
    print(
        f"Seeded user {user_id} (telegram_id {MOCK_TELEGRAM_ID}): "
        f"{len(HABITS)} activities, {log_count} logs over {DAYS} days. "
        f"Token written to {FRONTEND_ENV_FILE}."
    )


if __name__ == "__main__":
    asyncio.run(main())
