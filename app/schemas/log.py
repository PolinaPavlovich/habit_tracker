"""Pydantic schemas for journal entries."""

from datetime import date as date_type
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class LogBase(BaseModel):
    """Fields shared by every log representation."""

    activity_id: int = Field(gt=0)
    amount: Decimal = Field(gt=0, max_digits=10, decimal_places=2, examples=["5.00"])
    date: date_type | None = Field(
        default=None,
        description="Defaults to today when omitted.",
    )
    notes: str | None = Field(default=None, max_length=2000)


class LogCreate(LogBase):
    """Payload accepted by ``POST /logs/``."""


class LogUpdate(BaseModel):
    """Payload accepted by ``PATCH /logs/{log_id}``.

    Only ``amount`` is editable. ``extra="forbid"`` matters: without it a body
    carrying ``activity_id`` would be silently ignored, and a caller could
    believe it had moved an entry between activities. Re-parenting a log is a
    different operation needing its own ownership check on the target, so it is
    rejected here rather than half-honoured.
    """

    model_config = ConfigDict(extra="forbid")

    amount: Decimal = Field(gt=0, max_digits=10, decimal_places=2, examples=["5.00"])


class LogRead(LogBase):
    """Log entry as returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    date: date_type
    created_at: datetime


class LogListItem(BaseModel):
    """One row of ``GET /logs/``, joined with its activity.

    The activity's name and unit ride along because every consumer needs them
    to render a line, and the query has to visit ``activities`` anyway to prove
    ownership — so the join is free and saves the client an N+1.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    activity_id: int
    activity_name: str
    unit: str
    amount: Decimal
    date: date_type
    notes: str | None
    created_at: datetime
