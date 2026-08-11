"""Pydantic mirrors of the API's response payloads.

Responses are parsed into these models rather than poked at as dictionaries, so
a backend contract change fails loudly at the HTTP boundary instead of silently
producing a wrong message.
"""

from datetime import date as date_type
from decimal import Decimal

from pydantic import BaseModel


class Activity(BaseModel):
    """An activity as returned by ``GET /activities/``."""

    id: int
    name: str
    unit: str


class Log(BaseModel):
    """A journal entry as returned by ``POST /logs/``."""

    id: int
    activity_id: int
    amount: Decimal
    date: date_type


class ActivitySummary(BaseModel):
    """Totals for a single activity inside a summary window."""

    activity_id: int
    activity_name: str
    unit: str
    total_amount: Decimal
    entries_count: int


class Summary(BaseModel):
    """The payload of ``GET /logs/summary``."""

    period_start: date_type
    period_end: date_type
    days: int
    items: list[ActivitySummary]
