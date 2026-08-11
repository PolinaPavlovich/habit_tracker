"""ORM models. Imported here so Alembic autogenerate sees every table."""

from app.models.activity import Activity
from app.models.log import Log

__all__ = ["Activity", "Log"]
