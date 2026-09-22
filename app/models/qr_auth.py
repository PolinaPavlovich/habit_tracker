"""ORM model for QR login sessions.

A Smart TV cannot hold the bot's shared secret and cannot run Telegram, so it
proves nothing about itself. Instead it opens a short-lived session, shows the
id as a QR code, and waits for an already-authenticated phone to vouch for it.
"""

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class QrSessionStatus(enum.StrEnum):
    """Lifecycle of a QR login session.

    ``expired`` is deliberately absent. Lambda runs no scheduler, so nothing
    could ever write that state at the moment it becomes true; expiry is a
    property of ``expires_at`` versus now, evaluated on every read.
    """

    PENDING = "pending"
    APPROVED = "approved"
    CONSUMED = "consumed"


class QrAuthSession(Base, TimestampMixin):
    """One TV's attempt to log in, from QR render to token pickup."""

    __tablename__ = "qr_auth_sessions"

    id: Mapped[int] = mapped_column(primary_key=True)

    # The only thing the TV knows and the phone scans. 122 bits of randomness is
    # the actual defence against a third party claiming somebody else's session,
    # which is why it is a uuid4 rather than a sequence value.
    session_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        unique=True,
        index=True,
        nullable=False,
        default=uuid.uuid4,
    )

    # String-backed rather than a native PostgreSQL enum: altering a native
    # enum's members in Alembic is painful, and this one will likely gain a
    # state later.
    #
    # ``values_callable`` is load-bearing. SQLAlchemy persists a Python enum by
    # its *name* by default, which would store "PENDING" while migration 0003
    # declares the CHECK constraint over "pending" — every insert would fail.
    status: Mapped[QrSessionStatus] = mapped_column(
        Enum(
            QrSessionStatus,
            native_enum=False,
            length=16,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        default=QrSessionStatus.PENDING,
        nullable=False,
    )

    # Null until a phone approves. Nothing reads the session as authenticated
    # while this is null.
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
    )

    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        index=True,
        nullable=False,
    )
    approved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    consumed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Bounds how many times one session may be polled. Not a general rate
    # limit — each Lambda invocation may be a fresh container, so no in-process
    # counter is shared. A global limit belongs at the edge, not here.
    poll_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    def __repr__(self) -> str:
        return f"<QrAuthSession session_id={self.session_id} status={self.status}>"
