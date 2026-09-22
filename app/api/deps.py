"""Shared FastAPI dependencies."""

import secrets
from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import InitDataError, TokenError, decode_tv_token, verify_init_data
from app.crud import user_crud
from app.db.session import get_session
from app.models.user import User

SessionDep = Annotated[AsyncSession, Depends(get_session)]

_UNAUTHENTICATED = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Authentication required.",
)


async def get_current_user(
    session: SessionDep,
    authorization: Annotated[str | None, Header()] = None,
    x_telegram_id: Annotated[int | None, Header(alias="X-Telegram-Id")] = None,
    x_internal_api_key: Annotated[str | None, Header(alias="X-Internal-Api-Key")] = None,
    x_telegram_username: Annotated[str | None, Header(alias="X-Telegram-Username")] = None,
) -> User:
    """Resolve the tenant behind the request, provisioning them on first contact.

    Two schemes, chosen by whether ``Authorization`` is present, and never
    falling back from one to the other. A rejected ``Authorization`` must not be
    retryable as header auth, or the weaker path becomes a bypass for the
    stronger one.

    - ``Authorization: tma <initData>`` — a browser inside Telegram. Telegram's
      signature is what makes the identity trustworthy, so no shared secret is
      involved and nothing secret ships to the client.
    - ``Authorization: Bearer <jwt>`` — a device that earned a token through the
      QR handshake, typically a Smart TV that cannot run Telegram at all.
    - No ``Authorization`` — the bot, server side, presenting ``X-Telegram-Id``
      behind the shared secret in ``X-Internal-Api-Key``.

    Note the behaviour change: a request with no credentials at all used to be
    a 422 from FastAPI's own header validation, because both headers were
    required. They are optional now, so it is a 401. A non-numeric
    ``X-Telegram-Id`` is still a 422.
    """
    if authorization is not None:
        return await _user_from_authorization(session, authorization)
    return await _user_from_internal_headers(
        session,
        telegram_id=x_telegram_id,
        api_key=x_internal_api_key,
        username=x_telegram_username,
    )


async def _user_from_authorization(session: AsyncSession, authorization: str) -> User:
    """Resolve a browser caller from a signed Telegram ``initData`` payload."""
    scheme, _, credentials = authorization.partition(" ")
    if not credentials:
        raise _UNAUTHENTICATED
    if scheme.lower() == "bearer":
        return await _user_from_tv_token(session, credentials)
    if scheme.lower() != "tma":
        raise _UNAUTHENTICATED

    try:
        verified = verify_init_data(
            credentials,
            bot_token=settings.telegram_bot_token,
            max_age_seconds=settings.init_data_max_age_seconds,
        )
    except InitDataError as exc:
        # Deliberately one wording for forged, malformed and stale alike:
        # distinguishing them tells an attacker which half to keep working on.
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Telegram credentials.",
        ) from exc

    return await user_crud.get_or_create(
        session,
        telegram_id=verified.telegram_id,
        username=verified.username,
    )


async def _user_from_tv_token(session: AsyncSession, token: str) -> User:
    """Resolve a device that completed the QR handshake.

    The token names an internal user id, so ``user_crud.get`` — tenant-blind by
    design and therefore off limits for activities and logs — is exactly right
    here: the id *is* the tenant, and the signature is what vouched for it.

    A token whose user has since been deleted is rejected, not treated as a
    stale-but-harmless credential.
    """
    try:
        user_id = decode_tv_token(token, secret=settings.jwt_secret)
    except TokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid access token.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    user = await user_crud.get(session, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid access token.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


async def _user_from_internal_headers(
    session: AsyncSession,
    *,
    telegram_id: int | None,
    api_key: str | None,
    username: str | None,
) -> User:
    """Resolve the bot's caller: a tenant id vouched for by the shared secret.

    The id alone means nothing — without the secret any caller could name any
    tenant — so both headers are required together.
    """
    if telegram_id is None or api_key is None:
        raise _UNAUTHENTICATED
    if not secrets.compare_digest(api_key, settings.internal_api_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid internal API key.",
        )
    return await user_crud.get_or_create(
        session,
        telegram_id=telegram_id,
        username=username,
    )


CurrentUserDep = Annotated[User, Depends(get_current_user)]
