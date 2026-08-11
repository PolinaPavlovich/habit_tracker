"""Pydantic schemas for bot users."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class UserBase(BaseModel):
    """Fields shared by every user representation."""

    telegram_id: int = Field(gt=0, examples=[123456789])
    username: str | None = Field(default=None, max_length=64)


class UserCreate(UserBase):
    """Payload used when provisioning a user on first contact."""


class UserRead(UserBase):
    """User as returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
