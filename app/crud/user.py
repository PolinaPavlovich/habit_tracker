"""CRUD operations for bot users."""

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.base import CRUDBase
from app.models.user import User
from app.schemas.user import UserCreate


class CRUDUser(CRUDBase[User, UserCreate]):
    """User-specific queries on top of the generic CRUD base."""

    async def get_by_telegram_id(
        self,
        session: AsyncSession,
        telegram_id: int,
    ) -> User | None:
        """Return the user behind this Telegram id, or ``None``."""
        result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        return result.scalar_one_or_none()

    async def get_or_create(
        self,
        session: AsyncSession,
        *,
        telegram_id: int,
        username: str | None = None,
    ) -> User:
        """Provision the user on first contact, refreshing ``username`` afterwards.

        This runs on *every* authenticated request, so the settled case — a
        known user whose username has not changed — must stay a plain SELECT.
        Going straight to ``INSERT ... ON CONFLICT DO UPDATE`` would instead
        burn a sequence value and write a new row version per request, leaving
        ``users`` to bloat with dead tuples in proportion to traffic.

        First contact still falls through to the upsert, so two concurrent
        first messages from the same account cannot race into a duplicate-key
        error: the unique index on ``telegram_id`` arbitrates.
        """
        existing = await self.get_by_telegram_id(session, telegram_id)
        if existing is not None:
            if existing.username != username:
                existing.username = username
                await session.flush()
            return existing

        statement = (
            pg_insert(User)
            .values(telegram_id=telegram_id, username=username)
            .on_conflict_do_update(
                index_elements=[User.telegram_id],
                set_={"username": username},
            )
            .returning(User)
        )
        result = await session.execute(statement)
        return result.scalar_one()


user_crud: CRUDUser = CRUDUser(User)
