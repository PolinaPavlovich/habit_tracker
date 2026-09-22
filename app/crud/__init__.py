"""CRUD layer singletons."""

from app.crud.activity import activity_crud
from app.crud.log import log_crud
from app.crud.qr_auth import qr_auth_crud
from app.crud.user import user_crud

__all__ = ["activity_crud", "log_crud", "qr_auth_crud", "user_crud"]
