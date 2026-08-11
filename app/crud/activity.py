"""CRUD operations for activities."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.base import CRUDBase
from app.models.activity import Activity
from app.schemas.activity import ActivityCreate


class CRUDActivity(CRUDBase[Activity, ActivityCreate]):
    """Activity-specific queries on top of the generic CRUD base."""

    async def get_by_name(self, session: AsyncSession, name: str) -> Activity | None:
        """Return the activity with this exact name, or ``None``."""
        result = await session.execute(select(Activity).where(Activity.name == name))
        return result.scalar_one_or_none()


activity_crud: CRUDActivity = CRUDActivity(Activity)
