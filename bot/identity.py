"""The caller's Telegram identity, as sent to the API on every request."""

from dataclasses import dataclass

from aiogram.types import User as TelegramUser


class UnknownSenderError(RuntimeError):
    """Raised when an update carries no sender to attribute the action to."""


@dataclass(frozen=True, slots=True)
class Identity:
    """Who the API should treat this request as coming from."""

    telegram_id: int
    username: str | None


def require_identity(user: TelegramUser | None) -> Identity:
    """Build an :class:`Identity` from an update's sender.

    ``from_user`` is optional in aiogram's types (channel posts have no sender);
    such an update cannot be attributed to a tenant, so it is refused.
    """
    if user is None:
        raise UnknownSenderError("Update has no sender.")
    return Identity(telegram_id=user.id, username=user.username)
