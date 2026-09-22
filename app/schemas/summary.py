"""Pydantic schemas for aggregated statistics."""

from datetime import date as date_type
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class DailyBucket(BaseModel):
    """One day of an activity's history, zero-filled when nothing was logged.

    ``value`` is a ``Decimal`` so Pydantic emits it as a JSON *string*. A float
    here would reintroduce exactly the rounding drift that ``Numeric(10, 2)``
    exists to prevent, and the chart data would then be unsafe to feed back
    into a write.
    """

    date: date_type
    label: str
    value: Decimal


class ActivitySummary(BaseModel):
    """Totals for a single activity within the requested window."""

    model_config = ConfigDict(from_attributes=True)

    activity_id: int
    activity_name: str
    unit: str
    total_amount: Decimal
    entries_count: int
    weekly_stats: list[DailyBucket] = []


class SummaryResponse(BaseModel):
    """Aggregated statistics plus the window they were computed over."""

    period_start: date_type
    period_end: date_type
    days: int
    items: list[ActivitySummary]
