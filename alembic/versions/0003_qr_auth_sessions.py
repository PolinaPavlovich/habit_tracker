"""QR login sessions

Revision ID: 0003_qr_auth_sessions
Revises: 0002_multi_tenancy
Create Date: 2026-09-22

Adds the table backing QR login for devices that cannot run Telegram — a Smart
TV browser, primarily. Additive only: nothing existing is touched, so this runs
against an empty and a populated database alike, and ``downgrade`` is a plain
drop rather than the lossy reshaping ``0002`` needed.

``status`` is a plain ``VARCHAR(16)`` rather than a native PostgreSQL enum,
because altering a native enum's members later is markedly harder. SQLAlchemy's
``create_constraint`` defaults to False, so no CHECK is emitted on either side;
the allowed values are enforced by ``QrSessionStatus`` in the application.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003_qr_auth_sessions"
down_revision: str | None = "0002_multi_tenancy"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

STATUSES = ("pending", "approved", "consumed")


def upgrade() -> None:
    op.create_table(
        "qr_auth_sessions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("session_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column(
            "status",
            sa.Enum(*STATUSES, name="qrsessionstatus", native_enum=False, length=16),
            nullable=False,
        ),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("poll_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_qr_auth_sessions_session_id",
        "qr_auth_sessions",
        ["session_id"],
        unique=True,
    )
    # Every read filters on expiry, and the janitor in POST /qr-auth/init
    # deletes by it. Without this both are sequential scans.
    op.create_index(
        "ix_qr_auth_sessions_expires_at",
        "qr_auth_sessions",
        ["expires_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_qr_auth_sessions_expires_at", table_name="qr_auth_sessions")
    op.drop_index("ix_qr_auth_sessions_session_id", table_name="qr_auth_sessions")
    op.drop_table("qr_auth_sessions")
