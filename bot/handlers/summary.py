"""The ``/summary`` flow: aggregated totals, with switchable windows."""

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from bot.client import ApiError, HabitTrackerClient
from bot.config import settings
from bot.formatting import describe_api_error, format_summary
from bot.handlers.common import edit_message
from bot.identity import require_identity
from bot.keyboards import SummaryCB, summary_keyboard

router = Router(name="summary")


def _windows() -> tuple[int, ...]:
    """The offered windows, deduplicated and ordered."""
    return tuple(sorted({settings.summary_days, settings.summary_alt_days}))


@router.message(Command("summary"))
async def cmd_summary(message: Message, api: HabitTrackerClient) -> None:
    """Show the default window."""
    identity = require_identity(message.from_user)
    days = settings.summary_days
    try:
        summary = await api.get_summary(identity, days=days)
    except ApiError as error:
        await message.answer(describe_api_error(error))
        return

    await message.answer(
        format_summary(summary),
        reply_markup=summary_keyboard(days, _windows()),
    )


@router.callback_query(SummaryCB.filter())
async def cb_summary(
    callback: CallbackQuery,
    callback_data: SummaryCB,
    api: HabitTrackerClient,
) -> None:
    """Re-fetch for a different window and rewrite the same message."""
    await callback.answer()
    identity = require_identity(callback.from_user)
    try:
        summary = await api.get_summary(identity, days=callback_data.days)
    except ApiError as error:
        await edit_message(callback, describe_api_error(error))
        return

    await edit_message(
        callback,
        format_summary(summary),
        summary_keyboard(callback_data.days, _windows()),
    )
