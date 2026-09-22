"""CRUD operations for QR login sessions.

Every state change here is a *conditional* UPDATE whose WHERE clause carries the
state it expects to find. Two Lambda containers can serve two requests for the
same session at the same instant; a read-then-write would let both believe they
won. Letting PostgreSQL arbitrate — and treating "no row updated" as "somebody
else got there first" — is what makes approval and token pickup single-use.

Like the rest of the CRUD layer these ``flush`` and never ``commit``; the
session dependency owns the transaction.
"""

import uuid
from dataclasses import dataclass
from datetime import timedelta

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.qr_auth import QrAuthSession, QrSessionStatus


@dataclass(frozen=True, slots=True)
class PollSnapshot:
    """What one poll observed, after counting itself."""

    status: QrSessionStatus
    is_expired: bool
    poll_count: int


class CRUDQrAuth:
    """Queries for the QR login handshake.

    Unlike activities and logs, these are *not* scoped to a tenant. A session
    has no owner until it is approved, and the TV polling it has no identity to
    scope by — the unguessable ``session_id`` is the capability. That is why the
    project's "never look up by id alone" rule does not apply here. It still
    applies to ``approve``, which takes its ``user_id`` from the authenticated
    caller and never from the request body.
    """

    async def create_session(
        self,
        session: AsyncSession,
        *,
        ttl_seconds: int,
    ) -> QrAuthSession:
        """Open a pending session that expires ``ttl_seconds`` from now.

        Expiry is computed from the database clock, not this process's, so a
        Lambda container with a skewed clock cannot mint a session that outlives
        what every later query will measure it against.
        """
        row = QrAuthSession(
            session_id=uuid.uuid4(),
            status=QrSessionStatus.PENDING,
            expires_at=func.now() + timedelta(seconds=ttl_seconds),
        )
        session.add(row)
        await session.flush()
        await session.refresh(row)
        return row

    async def purge_expired(self, session: AsyncSession, *, grace_seconds: int) -> None:
        """Delete sessions well past their expiry.

        There is no scheduler on Lambda, so this is the only garbage collection
        the table gets: it runs opportunistically whenever a new session opens.
        The grace period keeps rows around long enough that a TV polling a
        just-expired session still gets a clean "expired" rather than a 404.
        """
        await session.execute(
            delete(QrAuthSession).where(
                QrAuthSession.expires_at < func.now() - timedelta(seconds=grace_seconds)
            )
        )

    async def approve(
        self,
        session: AsyncSession,
        *,
        session_id: uuid.UUID,
        user_id: int,
        grace_seconds: int,
    ) -> bool:
        """Attach an owner to a pending session. True if this call was the one that did.

        ``expires_at`` is pushed out by ``grace_seconds`` so an approval landing
        in the session's last second still leaves the TV a window to collect the
        token — otherwise a scan at t=119s would produce a token nobody could
        ever pick up.
        """
        result = await session.execute(
            update(QrAuthSession)
            .where(
                QrAuthSession.session_id == session_id,
                QrAuthSession.status == QrSessionStatus.PENDING,
                QrAuthSession.expires_at > func.now(),
            )
            .values(
                status=QrSessionStatus.APPROVED,
                user_id=user_id,
                approved_at=func.now(),
                expires_at=func.now() + timedelta(seconds=grace_seconds),
            )
            .returning(QrAuthSession.id)
        )
        return result.scalar_one_or_none() is not None

    async def claim_approved(
        self,
        session: AsyncSession,
        *,
        session_id: uuid.UUID,
    ) -> int | None:
        """Consume an approved session, returning its owner exactly once.

        The transition to ``consumed`` happens in the same statement that reads
        the approval, so concurrent polls cannot both be handed a token. If the
        winning response is then lost in transit the token is simply gone and
        the TV opens a new session — accepted, and cheaper than tracking
        delivery.
        """
        result = await session.execute(
            update(QrAuthSession)
            .where(
                QrAuthSession.session_id == session_id,
                QrAuthSession.status == QrSessionStatus.APPROVED,
                QrAuthSession.expires_at > func.now(),
            )
            .values(status=QrSessionStatus.CONSUMED, consumed_at=func.now())
            .returning(QrAuthSession.user_id)
        )
        return result.scalar_one_or_none()

    async def register_poll(
        self,
        session: AsyncSession,
        *,
        session_id: uuid.UUID,
    ) -> PollSnapshot | None:
        """Count this poll and report what it saw. ``None`` when no such session exists.

        Expiry is evaluated against the database clock in the same statement,
        rather than compared in Python afterwards, so the answer cannot drift
        between the read and the comparison.
        """
        result = await session.execute(
            update(QrAuthSession)
            .where(QrAuthSession.session_id == session_id)
            .values(poll_count=QrAuthSession.poll_count + 1)
            .returning(
                QrAuthSession.status,
                (QrAuthSession.expires_at <= func.now()).label("is_expired"),
                QrAuthSession.poll_count,
            )
        )
        row = result.one_or_none()
        if row is None:
            return None
        return PollSnapshot(
            status=row.status,
            is_expired=bool(row.is_expired),
            poll_count=row.poll_count,
        )

    async def get_by_session_id(
        self,
        session: AsyncSession,
        *,
        session_id: uuid.UUID,
    ) -> QrAuthSession | None:
        """Fetch one session by its public id."""
        result = await session.execute(
            select(QrAuthSession).where(QrAuthSession.session_id == session_id)
        )
        return result.scalar_one_or_none()


qr_auth_crud: CRUDQrAuth = CRUDQrAuth()
