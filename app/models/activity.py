"""ORM model for the activity dictionary."""

from typing import TYPE_CHECKING

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.log import Log


class Activity(Base, TimestampMixin):
    """A trackable activity, e.g. "Running" measured in kilometres."""

    __tablename__ = "activities"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    unit: Mapped[str] = mapped_column(String(32), nullable=False)

    logs: Mapped[list["Log"]] = relationship(
        back_populates="activity",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    def __repr__(self) -> str:
        return f"<Activity id={self.id} name={self.name!r} unit={self.unit!r}>"
