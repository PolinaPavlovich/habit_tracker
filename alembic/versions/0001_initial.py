"""Initial schema: activities and logs

Revision ID: 0001_initial
Revises:
Create Date: 2026-08-11

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "activities",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("unit", sa.String(length=32), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_activities"),
    )
    op.create_index("ix_activities_name", "activities", ["name"], unique=True)

    op.create_table(
        "logs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("activity_id", sa.Integer(), nullable=False),
        sa.Column("amount", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["activity_id"],
            ["activities.id"],
            name="fk_logs_activity_id_activities",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_logs"),
    )
    op.create_index("ix_logs_activity_id", "logs", ["activity_id"], unique=False)
    op.create_index("ix_logs_date", "logs", ["date"], unique=False)
    op.create_index(
        "ix_logs_activity_id_date",
        "logs",
        ["activity_id", "date"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_logs_activity_id_date", table_name="logs")
    op.drop_index("ix_logs_date", table_name="logs")
    op.drop_index("ix_logs_activity_id", table_name="logs")
    op.drop_table("logs")

    op.drop_index("ix_activities_name", table_name="activities")
    op.drop_table("activities")
