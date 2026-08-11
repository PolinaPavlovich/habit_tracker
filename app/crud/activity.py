"""CRUD operations for activities.

Every read here is scoped to an owner. The tenant-blind ``CRUDBase.get`` and
``CRUDBase.get_multi`` must not be used for activities — they would cross
user boundaries.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.base import CRUDBase
from app.models.activity import Activity
from app.schemas.activity import ActivityCreate


class CRUDActivity(CRUDBase[Activity, ActivityCreate]):
    """Activity-specific queries on top of the generic CRUD base."""

    async def get_by_name(
        self,
        session: AsyncSession,
        *,
        user_id: int,
        name: str,
    ) -> Activity | None:
        """Return this owner's activity with that exact name, or ``None``."""
        result = await session.execute(
            select(Activity).where(
                Activity.user_id == user_id,
                Activity.name == name,
            )
        )
        return result.scalar_one_or_none()

    async def get_for_user(
        self,
        session: AsyncSession,
        *,
        user_id: int,
        activity_id: int,
    ) -> Activity | None:
        """Return the activity only if it belongs to this owner.

        Returns ``None`` for another user's activity, so callers can treat it
        exactly like a missing row and avoid leaking its existence.
        """
        result = await session.execute(
            select(Activity).where(
                Activity.id == activity_id,
                Activity.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_multi_for_user(
        self,
        session: AsyncSession,
        *,
        user_id: int,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Activity]:
        """Return a page of this owner's activities, ordered by id."""
        statement = (
            select(Activity)
            .where(Activity.user_id == user_id)
            .order_by(Activity.id)
            .offset(skip)
            .limit(limit)
        )
        result = await session.execute(statement)
        return list(result.scalars().all())


activity_crud: CRUDActivity = CRUDActivity(Activity)
