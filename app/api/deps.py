"""Shared FastAPI dependencies."""

import secrets
from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.crud import user_crud
from app.db.session import get_session
from app.models.user import User

SessionDep = Annotated[AsyncSession, Depends(get_session)]


async def get_current_user(
    session: SessionDep,
    x_telegram_id: Annotated[int, Header(alias="X-Telegram-Id")],
    x_internal_api_key: Annotated[str, Header(alias="X-Internal-Api-Key")],
    x_telegram_username: Annotated[str | None, Header(alias="X-Telegram-Username")] = None,
) -> User:
    """Resolve the tenant behind the request, provisioning them on first contact.

    The shared secret is what makes the ``X-Telegram-Id`` header trustworthy —
    without it any caller could name any tenant. Missing or malformed headers
    are rejected by FastAPI itself with a 422.
    """
    if not secrets.compare_digest(x_internal_api_key, settings.internal_api_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid internal API key.",
        )
    return await user_crud.get_or_create(
        session,
        telegram_id=x_telegram_id,
        username=x_telegram_username,
    )


CurrentUserDep = Annotated[User, Depends(get_current_user)]
