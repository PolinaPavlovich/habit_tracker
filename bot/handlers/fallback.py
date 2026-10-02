"""Last in the router chain: button presses that nothing else recognised.

Inline keyboards stay tappable for as long as the message exists, and callback
payloads are parsed strictly — a button drawn by an older version of the bot,
whose payload has since gained or lost a field, matches no handler at all.
Without an answer Telegram leaves the button spinning.
"""

from aiogram import Router
from aiogram.types import CallbackQuery

router = Router(name="fallback")

STALE = "This menu is out of date. Send the command again."


@router.callback_query()
async def cb_unrecognised(callback: CallbackQuery) -> None:
    """Tell the user to reopen the menu instead of leaving a dead spinner."""
    await callback.answer(STALE, show_alert=True)
