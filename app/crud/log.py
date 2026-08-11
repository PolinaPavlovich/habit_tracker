"""CRUD operations and aggregations for journal entries."""

from datetime import date as date_type
from datetime import timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.base import CRUDBase
from app.models.activity import Activity
from app.models.log import Log
from app.schemas.log import LogCreate, LogListItem
from app.schemas.summary import ActivitySummary


class CRUDLog(CRUDBase[Log, LogCreate]):
    """Log-specific queries on top of the generic CRUD base.

    Every read here is scoped to an owner. ``logs`` carries no ``user_id`` of
    its own, so scoping always rides the join onto ``activities``. The
    tenant-blind ``CRUDBase.get`` must not be used for logs — it would happily
    return another user's entry by id.
    """

    async def get_for_user(
        self,
        session: AsyncSession,
        *,
        user_id: int,
        log_id: int,
    ) -> Log | None:
        """Return the entry only if it belongs to this owner.

        One query, not a fetch followed by an ownership check: the join is the
        check. Returns ``None`` for somebody else's entry so callers can treat
        it exactly like a missing row and avoid leaking its existence.
        """
        statement = (
            select(Log)
            .join(Activity, Activity.id == Log.activity_id)
            .where(Log.id == log_id, Activity.user_id == user_id)
        )
        result = await session.execute(statement)
        return result.scalar_one_or_none()

    async def get_recent_for_user(
        self,
        session: AsyncSession,
        *,
        user_id: int,
        limit: int,
        offset: int,
    ) -> list[LogListItem]:
        """Return a page of this owner's entries, newest first.

        Ordered by ``date`` descending with ``Log.id`` descending as the
        tiebreaker. The tiebreaker is required, not cosmetic: several entries
        routinely share a date, and ``date`` alone leaves their relative order
        up to PostgreSQL — which would let a paged read show one row twice and
        skip another.
        """
        statement = (
            select(
                Log.id.label("id"),
                Log.activity_id.label("activity_id"),
                Activity.name.label("activity_name"),
                Activity.unit.label("unit"),
                Log.amount.label("amount"),
                Log.date.label("date"),
                Log.notes.label("notes"),
                Log.created_at.label("created_at"),
            )
            .join(Activity, Activity.id == Log.activity_id)
            .where(Activity.user_id == user_id)
            .order_by(Log.date.desc(), Log.id.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await session.execute(statement)
        return [LogListItem.model_validate(row) for row in result.all()]

    async def count_for_user(self, session: AsyncSession, *, user_id: int) -> int:
        """Total number of entries this owner has, for pagination bounds."""
        statement = (
            select(func.count(Log.id))
            .join(Activity, Activity.id == Log.activity_id)
            .where(Activity.user_id == user_id)
        )
        result = await session.execute(statement)
        return int(result.scalar_one())

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
