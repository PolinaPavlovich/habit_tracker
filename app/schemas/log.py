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


class LogRead(LogBase):
    """Log entry as returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    date: date_type
    created_at: datetime
