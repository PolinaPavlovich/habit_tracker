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

from bot.schemas import Activity

CUSTOM_AMOUNT = "custom"


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


def cancel_keyboard() -> InlineKeyboardMarkup:
    """A single cancel button, offered while a flow is waiting for typed input."""
    builder = InlineKeyboardBuilder()
    builder.button(text="✖️ Cancel", callback_data=NavCB(action="cancel"))
    return builder.as_markup()


def format_preset(preset: Decimal) -> str:
    """Render a preset without trailing zeros, so 5 shows as "5", not "5.00"."""
    normalized = preset.normalize()
    return f"{normalized:f}"
