"""Pydantic schemas for the activity dictionary."""

from datetime import datetime
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ActivityBase(BaseModel):
    """Fields shared by every activity representation."""

    name: str = Field(min_length=1, max_length=100, examples=["Running"])
    unit: str = Field(min_length=1, max_length=32, examples=["km"])


class ActivityCreate(ActivityBase):
    """Payload accepted by ``POST /activities``."""


class ActivityUpdate(BaseModel):
    """Payload accepted by ``PATCH /activities/{activity_id}``.

    Either field may be sent alone. Unknown fields are rejected rather than
    ignored, so a caller can never believe it changed something it did not.
    """

    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=1, max_length=100, examples=["Jogging"])
    unit: str | None = Field(default=None, min_length=1, max_length=32, examples=["km"])

    @model_validator(mode="after")
    def _require_a_real_change(self) -> Self:
        """Reject an empty body and an explicit ``null``.

        Both columns are NOT NULL, and ``CRUDBase.update`` writes every field
        that was *sent*, so a ``null`` let through here would reach the
        database as a constraint violation instead of a 422.
        """
        if not self.model_fields_set:
            raise ValueError("Provide at least one of: name, unit.")
        for field in self.model_fields_set:
            if getattr(self, field) is None:
                raise ValueError(f"{field} cannot be null.")
        return self


class ActivityRead(ActivityBase):
    """Activity as returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime


class ActivityDetail(ActivityRead):
    """One activity plus how many journal entries hang off it.

    The count is what lets a client say what a delete will destroy before the
    user confirms it.
    """

    entries_count: int
