"""Inline keyboards and the typed callback data they carry.

Callback payloads are built through aiogram's ``CallbackData`` factories rather
than hand-formatted strings, so parsing is type-checked on the way back in.
Telegram caps callback data at 64 bytes — hence short prefixes and ids instead
of names.
"""

from collections.abc import Sequence
from decimal import Decimal
from typing import Literal

from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.schemas import Activity, LogEntry

CUSTOM_AMOUNT = "custom"
# Activity names are clipped past this in a history button; Telegram truncates
# long captions itself, and it drops the amount and date rather than the name.
MAX_LABEL_NAME = 18


class ActivityCB(CallbackData, prefix="act"):
    """The user picked an activity to log against."""

    activity_id: int


class AmountCB(CallbackData, prefix="amt"):
    """The user picked an amount, or asked to type one.

    ``value`` is the decimal rendered as text, or the ``custom`` sentinel.
    """

    activity_id: int
    value: str


class SummaryCB(CallbackData, prefix="sum"):
    """The user asked for a different summary window."""

    days: int


class NavCB(CallbackData, prefix="nav"):
    """Navigation that is not tied to a specific row."""

    action: Literal["back", "cancel", "new"]


class HistoryCB(CallbackData, prefix="hst"):
    """The user tapped one entry in ``/history`` to open its detail view."""

    log_id: int
    offset: int


class HistoryPageCB(CallbackData, prefix="hpg"):
    """Move to another page of the history, and the way back from a detail view.

    Deliberately not ``NavCB(action="back")``: that is already claimed by the
    ``/log`` flow's handler, whose router is consulted first, so a history Back
    button using it would drop the user into the activity picker instead.
    """

    offset: int


class LogEditCB(CallbackData, prefix="led"):
    """The user asked to change one entry's amount."""

    log_id: int
    offset: int


class LogDeleteCB(CallbackData, prefix="ldl"):
    """Delete one entry: ``confirm`` false asks, true carries it out.

    Both steps share a factory so the two-tap flow cannot drift apart.
    """

    log_id: int
    offset: int
    confirm: bool


def activities_keyboard(activities: Sequence[Activity]) -> InlineKeyboardMarkup:
    """One button per activity, two per row, plus a way to create another."""
    builder = InlineKeyboardBuilder()
    for activity in activities:
        builder.button(
            text=activity.name,
            callback_data=ActivityCB(activity_id=activity.id),
        )
    builder.adjust(2)

    footer = InlineKeyboardBuilder()
    footer.button(text="➕ New activity", callback_data=NavCB(action="new"))
    builder.attach(footer)
    return builder.as_markup()


def amounts_keyboard(
    activity_id: int,
    presets: Sequence[Decimal],
) -> InlineKeyboardMarkup:
    """Preset amounts, then an escape hatch for typing an exact value."""
    builder = InlineKeyboardBuilder()
    for preset in presets:
        builder.button(
            text=format_preset(preset),
            callback_data=AmountCB(activity_id=activity_id, value=str(preset)),
        )
    builder.adjust(len(presets) or 1)

    footer = InlineKeyboardBuilder()
    footer.button(
        text="✏️ Custom…",
        callback_data=AmountCB(activity_id=activity_id, value=CUSTOM_AMOUNT),
    )
    footer.button(text="⬅️ Back", callback_data=NavCB(action="back"))
    footer.adjust(1)
    builder.attach(footer)
    return builder.as_markup()


def summary_keyboard(current_days: int, options: Sequence[int]) -> InlineKeyboardMarkup:
    """Window switches, with the active one marked."""
    builder = InlineKeyboardBuilder()
    for days in options:
        marker = "• " if days == current_days else ""
        builder.button(
            text=f"{marker}{days} days",
            callback_data=SummaryCB(days=days),
        )
    builder.adjust(len(options) or 1)
    return builder.as_markup()


def history_keyboard(
    entries: Sequence[LogEntry],
    *,
    offset: int,
    page_size: int,
    has_more: bool,
) -> InlineKeyboardMarkup:
    """One button per entry, newest first, with paging when there is more.

    Entries get a row each: an activity name plus amount and date is too wide to
    pair up without Telegram truncating it.
    """
    builder = InlineKeyboardBuilder()
    for entry in entries:
        builder.button(
            text=history_button_label(entry),
            callback_data=HistoryCB(log_id=entry.id, offset=offset),
        )
    builder.adjust(1)

    pager = InlineKeyboardBuilder()
    if offset > 0:
        pager.button(
            text="⬅️ Newer",
            callback_data=HistoryPageCB(offset=max(0, offset - page_size)),
        )
    if has_more:
        pager.button(
            text="Older ➡️",
            callback_data=HistoryPageCB(offset=offset + page_size),
        )
    pager.adjust(2)
    builder.attach(pager)
    return builder.as_markup()


def history_entry_keyboard(log_id: int, offset: int) -> InlineKeyboardMarkup:
    """Actions for a single entry: edit its amount, delete it, or go back."""
    builder = InlineKeyboardBuilder()
    builder.button(
        text="✏️ Edit amount",
        callback_data=LogEditCB(log_id=log_id, offset=offset),
    )
    builder.button(
        text="🗑 Delete",
        callback_data=LogDeleteCB(log_id=log_id, offset=offset, confirm=False),
    )
    builder.adjust(2)

    footer = InlineKeyboardBuilder()
    footer.button(text="⬅️ Back", callback_data=HistoryPageCB(offset=offset))
    builder.attach(footer)
    return builder.as_markup()


def delete_confirm_keyboard(log_id: int, offset: int) -> InlineKeyboardMarkup:
    """The second tap of a deletion, kept separate because it cannot be undone."""
    builder = InlineKeyboardBuilder()
    builder.button(
        text="✅ Yes, delete",
        callback_data=LogDeleteCB(log_id=log_id, offset=offset, confirm=True),
    )
    builder.button(
        text="✖️ Keep it",
        callback_data=HistoryCB(log_id=log_id, offset=offset),
    )
    builder.adjust(1)
    return builder.as_markup()


def history_button_label(entry: LogEntry) -> str:
    """One history row: activity, amount with unit, and the day it landed on.

    Telegram truncates long button captions, so the activity name is clipped
    first — the amount and date carry more of what distinguishes two rows.
    """
    name = entry.activity_name
    if len(name) > MAX_LABEL_NAME:
        name = f"{name[: MAX_LABEL_NAME - 1]}…"
    amount = format_preset(entry.amount)
    return f"{name} · {amount} {entry.unit} · {entry.date:%d %b}"


def cancel_keyboard() -> InlineKeyboardMarkup:
    """A single cancel button, offered while a flow is waiting for typed input."""
    builder = InlineKeyboardBuilder()
    builder.button(text="✖️ Cancel", callback_data=NavCB(action="cancel"))
    return builder.as_markup()


def format_preset(preset: Decimal) -> str:
    """Render a preset without trailing zeros, so 5 shows as "5", not "5.00"."""
    normalized = preset.normalize()
    return f"{normalized:f}"
