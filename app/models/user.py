"""ORM model for bot users."""

from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.activity import Activity


class User(Base, TimestampMixin):
    """A tenant. Every activity — and through it, every log — belongs to one."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    # Telegram ids already exceed 32 bits, so Integer is not wide enough.
    telegram_id: Mapped[int] = mapped_column(
        BigInteger,
        unique=True,
        index=True,
        nullable=False,
    )
    username: Mapped[str | None] = mapped_column(String(64), nullable=True)

    activities: Mapped[list["Activity"]] = relationship(
        back_populates="owner",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} telegram_id={self.telegram_id}>"
