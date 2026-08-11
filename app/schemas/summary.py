"""Pydantic schemas for aggregated statistics."""

from datetime import date as date_type
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class ActivitySummary(BaseModel):
    """Totals for a single activity within the requested window."""

    model_config = ConfigDict(from_attributes=True)

    activity_id: int
    activity_name: str
    unit: str
    total_amount: Decimal
    entries_count: int


class SummaryResponse(BaseModel):
    """Aggregated statistics plus the window they were computed over."""

    period_start: date_type
    period_end: date_type
    days: int
    items: list[ActivitySummary]
