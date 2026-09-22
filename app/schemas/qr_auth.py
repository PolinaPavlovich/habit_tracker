"""Pydantic schemas for QR login."""

import uuid
from datetime import datetime

from pydantic import BaseModel


class QrInitResponse(BaseModel):
    """Handed to a device that has just opened a login session."""

    session_id: uuid.UUID
    # Built server-side so the TV never has to know the bot's username or how a
    # Telegram deep link is shaped. It renders this string as a QR, nothing more.
    approve_url: str
    expires_at: datetime
    poll_interval_seconds: int


class QrPollResponse(BaseModel):
    """The answer to one poll.

    Deliberately one model with optional fields rather than a union of three.
    FastAPI validates a union member by member and returns the first that fits;
    a "pending" model whose only field is ``status`` would match an approved
    payload too, and silently strip the token off the one response that carries
    it.
    """

    status: str
    access_token: str | None = None
    token_type: str | None = None
    expires_in: int | None = None


class QrApproveResponse(BaseModel):
    """Confirmation for the phone that approved a session.

    Carries no token on purpose: the phone must never receive the credential it
    just granted to a different device.
    """

    status: str = "approved"
