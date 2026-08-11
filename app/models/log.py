"""ORM model for journal entries."""

from datetime import date as date_type
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Date, ForeignKey, Index, Numeric, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.activity import Activity


class Log(Base, TimestampMixin):
    """A single recorded amount of an activity on a given day."""

    __tablename__ = "logs"
    __table_args__ = (Index("ix_logs_activity_id_date", "activity_id", "date"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    activity_id: Mapped[int] = mapped_column(
        ForeignKey("activities.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    date: Mapped[date_type] = mapped_column(Date, index=True, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    activity: Mapped["Activity"] = relationship(back_populates="logs")

    def __repr__(self) -> str:
        return f"<Log id={self.id} activity_id={self.activity_id} amount={self.amount}>"
