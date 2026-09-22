"""Endpoints for logging a second device in by QR code.

The device that needs a token (a Smart TV browser) cannot prove anything about
itself, so it never authenticates here. It opens a session, displays the id,
and waits. A phone that *is* authenticated — through Telegram Mini App
``initData`` — vouches for the session, and only then does a token exist.
"""

import uuid

from fastapi import APIRouter, HTTPException, status

from app.api.deps import CurrentUserDep, SessionDep
from app.core.config import settings
from app.core.security import create_tv_token
from app.crud.qr_auth import qr_auth_crud
from app.models.qr_auth import QrSessionStatus
from app.schemas.qr_auth import QrApproveResponse, QrInitResponse, QrPollResponse

router = APIRouter(prefix="/qr-auth", tags=["qr-auth"])

# What the TV is told to wait between polls.
POLL_INTERVAL_SECONDS = 3
# An approval extends the session by this much, so a scan in the final second
# still leaves the TV time to collect its token.
APPROVAL_GRACE_SECONDS = 30
# Expired rows are kept this long past expiry so a TV polling a session that
# just lapsed is told "expired" rather than being sent away with a 404.
PURGE_GRACE_SECONDS = 3600
# A session polled far more than its lifetime allows is being probed, not used:
# at one poll every 3s a 120s session needs roughly 40.
MAX_POLLS = 200

# Every failure below is the same 404 with the same wording. Unknown, expired
# past the grace period, already consumed and never-existed are indistinguishable
# on purpose — anything finer is an oracle telling an attacker which guesses
# were close.
_UNKNOWN_SESSION = HTTPException(
    status_code=status.HTTP_404_NOT_FOUND,
    detail="No such login session.",
)


@router.post(
    "/init",
    response_model=QrInitResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Open a QR login session",
)
async def init_session(session: SessionDep) -> QrInitResponse:
    """Start a login session for a device that cannot authenticate itself.

    Unauthenticated by necessity — the caller has no identity yet; that is the
    whole point. The session it receives grants nothing until a phone approves
    it, so an attacker spamming this endpoint gets a pile of rows that expire
    into nothing.
    """
    # The only garbage collection this table gets. Lambda runs no scheduler, so
    # housekeeping rides along with the one request that is already writing.
    await qr_auth_crud.purge_expired(session, grace_seconds=PURGE_GRACE_SECONDS)

    row = await qr_auth_crud.create_session(
        session,
        ttl_seconds=settings.qr_session_ttl_seconds,
    )
    return QrInitResponse(
        session_id=row.session_id,
        approve_url=(
            f"https://t.me/{settings.telegram_bot_username}?startapp=qr_{row.session_id.hex}"
        ),
        expires_at=row.expires_at,
        poll_interval_seconds=POLL_INTERVAL_SECONDS,
    )


@router.get(
    "/poll/{session_id}",
    response_model=QrPollResponse,
    summary="Ask whether a QR login session has been approved",
)
async def poll_session(session_id: uuid.UUID, session: SessionDep) -> QrPollResponse:
    """Report a session's state, delivering its token exactly once.

    The approved branch is tried first and is itself the state transition, so
    two polls racing on two Lambda containers cannot both be handed a token —
    only the one whose UPDATE matched a row gets to mint it.
    """
    user_id = await qr_auth_crud.claim_approved(session, session_id=session_id)
    if user_id is not None:
        token = create_tv_token(
            user_id=user_id,
            secret=settings.jwt_secret,
            ttl_seconds=settings.jwt_ttl_seconds,
        )
        return QrPollResponse(
            status="approved",
            access_token=token,
            token_type="bearer",
            expires_in=settings.jwt_ttl_seconds,
        )

    snapshot = await qr_auth_crud.register_poll(session, session_id=session_id)
    if snapshot is None or snapshot.status is QrSessionStatus.CONSUMED:
        # Already-consumed reads as never-existed: a replayed session id must
        # not be distinguishable from a guessed one.
        raise _UNKNOWN_SESSION
    if snapshot.poll_count > MAX_POLLS:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many polls for this session.",
        )
    if snapshot.is_expired:
        return QrPollResponse(status="expired")
    return QrPollResponse(status="pending")


@router.post(
    "/approve/{session_id}",
    response_model=QrApproveResponse,
    summary="Approve a QR login session for the calling account",
)
async def approve_session(
    session_id: uuid.UUID,
    session: SessionDep,
    user: CurrentUserDep,
) -> QrApproveResponse:
    """Grant the scanned session to the authenticated caller.

    The owner comes from the verified credential, never from the request, so a
    caller cannot approve a session into somebody else's account. The response
    carries no token: the phone is granting access to a *different* device and
    has no business holding the result.
    """
    approved = await qr_auth_crud.approve(
        session,
        session_id=session_id,
        user_id=user.id,
        grace_seconds=APPROVAL_GRACE_SECONDS,
    )
    if not approved:
        raise _UNKNOWN_SESSION
    return QrApproveResponse()
