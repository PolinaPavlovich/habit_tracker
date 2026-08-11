"""Multi-tenancy: users, per-user activities

Revision ID: 0002_multi_tenancy
Revises: 0001_initial
Create Date: 2026-08-11

Adds the ``users`` table and scopes ``activities`` to an owner. ``logs`` is
untouched: ownership is derived through ``logs.activity_id -> activities.user_id``.

Existing activities predate the concept of an owner, so they are handed to a
single bootstrap user (``telegram_id = 0``) which is created only if there is
anything to adopt. That keeps the migration runnable against both an empty and
a populated database.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002_multi_tenancy"
down_revision: str | None = "0001_initial"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

BOOTSTRAP_TELEGRAM_ID = 0
BOOTSTRAP_USERNAME = "legacy"


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("telegram_id", sa.BigInteger(), nullable=False),
        sa.Column("username", sa.String(length=64), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_users"),
    )
    op.create_index("ix_users_telegram_id", "users", ["telegram_id"], unique=True)

    # Nullable first, so the column can be added to a table that already has rows.
    op.add_column("activities", sa.Column("user_id", sa.Integer(), nullable=True))

    bind = op.get_bind()
    orphan_count = bind.execute(
        sa.text("SELECT count(*) FROM activities WHERE user_id IS NULL")
    ).scalar_one()
    if orphan_count:
        bootstrap_id = bind.execute(
            sa.text(
                "INSERT INTO users (telegram_id, username) "
                "VALUES (:telegram_id, :username) RETURNING id"
            ),
            {
                "telegram_id": BOOTSTRAP_TELEGRAM_ID,
                "username": BOOTSTRAP_USERNAME,
            },
        ).scalar_one()
        bind.execute(
            sa.text("UPDATE activities SET user_id = :user_id WHERE user_id IS NULL"),
            {"user_id": bootstrap_id},
        )

    op.alter_column("activities", "user_id", existing_type=sa.Integer(), nullable=False)
    op.create_foreign_key(
        "fk_activities_user_id_users",
        "activities",
        "users",
        ["user_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index("ix_activities_user_id", "activities", ["user_id"], unique=False)

    # Names are unique per owner from here on, not globally.
    op.drop_index("ix_activities_name", table_name="activities")
    op.create_index("ix_activities_name", "activities", ["name"], unique=False)
    op.create_unique_constraint(
        "uq_activities_user_id_name",
        "activities",
        ["user_id", "name"],
    )


def downgrade() -> None:
    # A global unique index on ``name`` cannot coexist with the same name owned
    # by two users, so keep a single owner's activities and drop the rest.
    # Logs follow via the existing ON DELETE CASCADE.
    bind = op.get_bind()
    keep_id = bind.execute(
        sa.text("SELECT id FROM users WHERE telegram_id = :telegram_id"),
        {"telegram_id": BOOTSTRAP_TELEGRAM_ID},
    ).scalar_one_or_none()
    if keep_id is None:
        keep_id = bind.execute(sa.text("SELECT min(id) FROM users")).scalar_one_or_none()
    if keep_id is None:
        bind.execute(sa.text("DELETE FROM activities"))
    else:
        bind.execute(
            sa.text("DELETE FROM activities WHERE user_id <> :keep_id"),
            {"keep_id": keep_id},
        )

    op.drop_constraint("uq_activities_user_id_name", "activities", type_="unique")
    op.drop_index("ix_activities_name", table_name="activities")
    op.create_index("ix_activities_name", "activities", ["name"], unique=True)

    op.drop_index("ix_activities_user_id", table_name="activities")
    op.drop_constraint("fk_activities_user_id_users", "activities", type_="foreignkey")
    op.drop_column("activities", "user_id")

    op.drop_index("ix_users_telegram_id", table_name="users")
    op.drop_table("users")
