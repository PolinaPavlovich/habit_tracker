"""Pydantic schemas for the activity dictionary."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ActivityBase(BaseModel):
    """Fields shared by every activity representation."""

    name: str = Field(min_length=1, max_length=100, examples=["Running"])
    unit: str = Field(min_length=1, max_length=32, examples=["km"])


class ActivityCreate(ActivityBase):
    """Payload accepted by ``POST /activities/``."""


class ActivityRead(ActivityBase):
    """Activity as returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
