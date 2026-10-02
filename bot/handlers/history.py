"""The ``/history`` flow: browse recent entries, then amend or remove one.

Only journal entries are touched here. Deleting an entry leaves its activity in
place — removing an activity lives in ``/habits``.

The same screens also serve the "Entries" button of one activity in
``/habits``: every callback carries an ``activity_id``, where
``ALL_ACTIVITIES`` means the whole journal.
"""

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.client import ApiError, HabitTrackerClient
from bot.formatting import (
    describe_api_error,
    format_delete_prompt,
    format_history_entry,
    format_history_header,
    format_log_deleted,
    format_log_updated,
    parse_amount,
)
from bot.handlers.common import edit_message
from bot.identity import Identity, require_identity
from bot.keyboards import (
    ALL_ACTIVITIES,
    HistoryCB,
    HistoryPageCB,
    LogDeleteCB,
    LogEditCB,
    cancel_keyboard,
    delete_confirm_keyboard,
    history_entry_keyboard,
    history_keyboard,
)
from bot.schemas import LogEntry
from bot.states import HistoryStates

router = Router(name="history")

PAGE_SIZE = 10
EMPTY = "📋 Nothing logged yet. Send /log to record something."
EMPTY_FOR_ACTIVITY = "📋 Nothing logged for this activity yet. Send /log to record something."
GONE = "⚠️ That entry is already gone."


@router.message(Command("history"))
async def cmd_history(
    message: Message,
    state: FSMContext,
    api: HabitTrackerClient,
) -> None:
    """Open the first page of the user's journal."""
    await state.clear()
    identity = require_identity(message.from_user)
    page = await _fetch_page(api, identity, offset=0)
    if isinstance(page, str):
        await message.answer(page)
        return

    entries, has_more = page
    if not entries:
        await message.answer(EMPTY)
        return
    await message.answer(
        format_history_header(0, PAGE_SIZE),
        reply_markup=history_keyboard(
            entries,
            offset=0,
            page_size=PAGE_SIZE,
            has_more=has_more,
        ),
    )


@router.callback_query(HistoryPageCB.filter())
async def cb_page(
    callback: CallbackQuery,
    callback_data: HistoryPageCB,
    state: FSMContext,
    api: HabitTrackerClient,
) -> None:
    """Render another page — and the way back out of a detail view."""
    await callback.answer()
    await state.set_state(None)
    await _render_page(callback, api, callback_data.offset, callback_data.activity_id)


@router.callback_query(HistoryCB.filter())
async def cb_open_entry(
    callback: CallbackQuery,
    callback_data: HistoryCB,
    state: FSMContext,
    api: HabitTrackerClient,
) -> None:
    """Show one entry with its edit and delete actions."""
    await callback.answer()
    await state.set_state(None)
    identity = require_identity(callback.from_user)
    entry = await _find(api, identity, callback_data)
    if entry is None:
        await _render_page(
            callback, api, callback_data.offset, callback_data.activity_id, notice=GONE
        )
        return

    await edit_message(
        callback,
        format_history_entry(entry),
        history_entry_keyboard(entry.id, callback_data.offset, callback_data.activity_id),
    )


@router.callback_query(LogEditCB.filter())
async def cb_edit(
    callback: CallbackQuery,
    callback_data: LogEditCB,
    state: FSMContext,
    api: HabitTrackerClient,
) -> None:
    """Ask for the replacement amount."""
    await callback.answer()
    identity = require_identity(callback.from_user)
    entry = await _find(api, identity, callback_data)
    if entry is None:
        await _render_page(
            callback, api, callback_data.offset, callback_data.activity_id, notice=GONE
        )
        return

    await state.set_state(HistoryStates.waiting_new_amount)
    await state.update_data(
        log_id=entry.id,
        offset=callback_data.offset,
        activity_name=entry.activity_name,
        unit=entry.unit,
    )
    await edit_message(
        callback,
        f"{format_history_entry(entry)}\n\nSend me the new amount ({entry.unit}).",
        cancel_keyboard(),
    )


@router.message(HistoryStates.waiting_new_amount)
async def on_new_amount(
    message: Message,
    state: FSMContext,
    api: HabitTrackerClient,
) -> None:
    """Validate the typed amount and patch the entry.

    A rejected value leaves the state in place so the user can try again.
    """
    try:
        amount = parse_amount(message.text or "")
    except ValueError as error:
        await message.answer(f"⚠️ {error}")
        return

    data = await state.get_data()
    log_id = data.get("log_id")
    if not isinstance(log_id, int):
        await state.clear()
        await message.answer("⚠️ I lost track of that one. Send /history to start over.")
        return

    identity = require_identity(message.from_user)
    try:
        await api.update_log(identity, log_id=log_id, amount=amount)
    except ApiError as error:
        await state.clear()
        await message.answer(GONE if error.status_code == 404 else describe_api_error(error))
        return

    await state.clear()
    await message.answer(
        format_log_updated(
            str(data.get("activity_name", "")),
            str(data.get("unit", "")),
            amount,
        )
    )


@router.callback_query(LogDeleteCB.filter(F.confirm.is_(False)))
async def cb_delete_ask(
    callback: CallbackQuery,
    callback_data: LogDeleteCB,
    api: HabitTrackerClient,
) -> None:
    """Confirm before removing, since nothing here can be undone."""
    await callback.answer()
    identity = require_identity(callback.from_user)
    entry = await _find(api, identity, callback_data)
    if entry is None:
        await _render_page(
            callback, api, callback_data.offset, callback_data.activity_id, notice=GONE
        )
        return

    await edit_message(
        callback,
        format_delete_prompt(entry),
        delete_confirm_keyboard(entry.id, callback_data.offset, callback_data.activity_id),
    )


@router.callback_query(LogDeleteCB.filter(F.confirm.is_(True)))
async def cb_delete_confirm(
    callback: CallbackQuery,
    callback_data: LogDeleteCB,
    api: HabitTrackerClient,
) -> None:
    """Carry the deletion out and report what went."""
    await callback.answer()
    identity = require_identity(callback.from_user)
    entry = await _find(api, identity, callback_data)
    if entry is None:
        await _render_page(
            callback, api, callback_data.offset, callback_data.activity_id, notice=GONE
        )
        return

    try:
        await api.delete_log(identity, log_id=entry.id)
    except ApiError as error:
        # A double tap loses the race against itself; the entry is gone either
        # way, which is the outcome the user asked for.
        if error.status_code != 404:
            await edit_message(callback, describe_api_error(error))
            return

    await edit_message(callback, format_log_deleted(entry))


async def _fetch_page(
    api: HabitTrackerClient,
    identity: Identity,
    *,
    offset: int,
    activity_id: int = ALL_ACTIVITIES,
) -> tuple[list[LogEntry], bool] | str:
    """Fetch one page, or return the message to show if the call failed.

    One extra row is requested so that "is there a next page" is answered
    without a second round trip or a count endpoint.
    """
    try:
        entries = await api.list_logs(
            identity,
            limit=PAGE_SIZE + 1,
            offset=offset,
            activity_id=None if activity_id == ALL_ACTIVITIES else activity_id,
        )
    except ApiError as error:
        return describe_api_error(error)
    return entries[:PAGE_SIZE], len(entries) > PAGE_SIZE


async def _render_page(
    callback: CallbackQuery,
    api: HabitTrackerClient,
    offset: int,
    activity_id: int = ALL_ACTIVITIES,
    *,
    notice: str | None = None,
) -> None:
    """Rewrite the message with a page of history, optionally led by a notice."""
    identity = require_identity(callback.from_user)
    page = await _fetch_page(api, identity, offset=offset, activity_id=activity_id)
    if isinstance(page, str):
        await edit_message(callback, page)
        return

    entries, has_more = page
    filtered = activity_id != ALL_ACTIVITIES
    if not entries:
        # The page may have emptied under us — fall back to the first one rather
        # than stranding the user on an offset past the end.
        if offset > 0:
            await _render_page(callback, api, 0, activity_id, notice=notice)
            return
        empty = EMPTY_FOR_ACTIVITY if filtered else EMPTY
        await edit_message(
            callback,
            f"{notice}\n\n{empty}" if notice else empty,
            # Keeps the way back to the activity; no keyboard at all otherwise.
            history_keyboard(
                [], offset=0, page_size=PAGE_SIZE, has_more=False, activity_id=activity_id
            )
            if filtered
            else None,
        )
        return

    # Every row of a narrowed page belongs to the one activity, so the first
    # row's name is the heading and no extra call is needed to learn it.
    header = format_history_header(
        offset,
        PAGE_SIZE,
        entries[0].activity_name if filtered else None,
    )
    await edit_message(
        callback,
        f"{notice}\n\n{header}" if notice else header,
        history_keyboard(
            entries,
            offset=offset,
            page_size=PAGE_SIZE,
            has_more=has_more,
            activity_id=activity_id,
        ),
    )


async def _find(
    api: HabitTrackerClient,
    identity: Identity,
    where: HistoryCB | LogEditCB | LogDeleteCB,
) -> LogEntry | None:
    """Locate one entry on its page.

    History keyboards stay tappable indefinitely, so an id from an old message
    may name an entry that has since been edited or deleted. Re-reading the page
    keeps what is shown honest, and doubles as the ownership check: the API only
    ever lists this user's own entries.
    """
    page = await _fetch_page(
        api,
        identity,
        offset=where.offset,
        activity_id=where.activity_id,
    )
    if isinstance(page, str):
        return None
    entries, _ = page
    return next((entry for entry in entries if entry.id == where.log_id), None)
