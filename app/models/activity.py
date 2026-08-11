"""ORM model for the activity dictionary."""

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.log import Log
    from app.models.user import User


class Activity(Base, TimestampMixin):
    """A trackable activity, e.g. "Running" measured in kilometres.

    Names are unique *per owner*, not globally: two users may each track their
    own "Running".
    """

    __tablename__ = "activities"
    __table_args__ = (
        UniqueConstraint("user_id", "name", name="uq_activities_user_id_name"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    unit: Mapped[str] = mapped_column(String(32), nullable=False)

    owner: Mapped["User"] = relationship(back_populates="activities")
    logs: Mapped[list["Log"]] = relationship(
        back_populates="activity",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    def __repr__(self) -> str:
        return f"<Activity id={self.id} user_id={self.user_id} name={self.name!r}>"
