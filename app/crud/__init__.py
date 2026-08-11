"""CRUD layer singletons."""

from app.crud.activity import activity_crud
from app.crud.log import log_crud

__all__ = ["activity_crud", "log_crud"]
