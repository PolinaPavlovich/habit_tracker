"""CRUD operations and aggregations for journal entries."""

from datetime import date as date_type
from datetime import timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.base import CRUDBase
from app.models.activity import Activity
from app.models.log import Log
from app.schemas.log import LogCreate
from app.schemas.summary import ActivitySummary


class CRUDLog(CRUDBase[Log, LogCreate]):
    """Log-specific queries on top of the generic CRUD base."""

    async def get_summary(
        self,
        session: AsyncSession,
        *,
        user_id: int,
        period_start: date_type,
        period_end: date_type,
    ) -> list[ActivitySummary]:
        """Aggregate one owner's logged amounts per activity over a date range.

        The range is inclusive. The sum and the count are computed by
        PostgreSQL, not in Python.

        Scoping happens on ``Activity.user_id``: ``logs`` carries no owner
        column of its own, and the join onto ``activities`` was already needed
        for the name and unit.

        Rows are ordered by ``total_amount`` descending, with ``Activity.id``
        ascending as a tiebreaker so that equal totals keep a stable, repeatable
        order across requests.
        """
        statement = (
            select(
                Activity.id.label("activity_id"),
                Activity.name.label("activity_name"),
                Activity.unit.label("unit"),
                func.sum(Log.amount).label("total_amount"),
                func.count(Log.id).label("entries_count"),
            )
            .join(Log, Log.activity_id == Activity.id)
            .where(
                Activity.user_id == user_id,
                Log.date >= period_start,
                Log.date <= period_end,
            )
            .group_by(Activity.id, Activity.name, Activity.unit)
            .order_by(func.sum(Log.amount).desc(), Activity.id.asc())
        )
        result = await session.execute(statement)
        return [ActivitySummary.model_validate(row) for row in result.all()]

    @staticmethod
    def period_bounds(days: int, today: date_type | None = None) -> tuple[date_type, date_type]:
        """Return the inclusive ``(start, end)`` window covering the last ``days`` days.

        The window includes today, so ``days=7`` yields ``today - 6 .. today``.
        """
        end = today if today is not None else date_type.today()
        return end - timedelta(days=days - 1), end


log_crud: CRUDLog = CRUDLog(Log)
