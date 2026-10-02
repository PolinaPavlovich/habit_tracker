"""The ``/habits`` flow: look at one activity, rename it, re-unit it, or delete it.

Deleting an activity deletes every entry logged under it. That is the one
irreversible action in the bot that removes more than a single row, so its
prompt always states how many entries go with it.
"""

from html import escape

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.client import ApiError, HabitTrackerClient
from bot.formatting import (
    describe_api_error,
    format_habit,
    format_habit_delete_prompt,
    format_habit_deleted,
)
from bot.handlers.activities import MAX_NAME_LENGTH, MAX_UNIT_LENGTH
from bot.handlers.common import edit_message
from bot.identity import require_identity
from bot.keyboards import (
    HabitCB,
    HabitDeleteCB,
    HabitEditCB,
    HabitListCB,
    cancel_keyboard,
    habit_delete_confirm_keyboard,
    habit_keyboard,
    habits_keyboard,
)
from bot.schemas import ActivityDetail
from bot.states import HabitStates

router = Router(name="habits")

LIST_HEADER = "🗂 <b>Your activities</b>\n\nTap one to rename it, change its unit or delete it."
EMPTY = "🗂 You have no activities yet."
GONE = "⚠️ That activity is already gone."
LOST = "⚠️ I lost track of that one. Send /habits to start over."


def _is_not_a_command(message: Message) -> bool:
    """True for ordinary text.

    The typed-input handlers below would otherwise save "/log" as the new name.
    Skipping commands lets them fall through to the router that owns them.
    """
    return not (message.text or "").startswith("/")


@router.message(Command("habits"))
async def cmd_habits(
    message: Message,
    state: FSMContext,
    api: HabitTrackerClient,
) -> None:
    """List the user's activities."""
    await state.clear()
    identity = require_identity(message.from_user)
    try:
        activities = await api.list_activities(identity)
    except ApiError as error:
        await message.answer(describe_api_error(error))
        return
    await message.answer(
        LIST_HEADER if activities else EMPTY,
        reply_markup=habits_keyboard(activities),
    )


@router.callback_query(HabitListCB.filter())
async def cb_list(
    callback: CallbackQuery,
    state: FSMContext,
    api: HabitTrackerClient,
) -> None:
    """Back to the list from one activity's screen."""
    await callback.answer()
    await state.set_state(None)
    await _render_list(callback, api)


@router.callback_query(HabitCB.filter())
async def cb_open(
    callback: CallbackQuery,
    callback_data: HabitCB,
    state: FSMContext,
    api: HabitTrackerClient,
) -> None:
    """Show one activity with everything that can be done to it."""
    await callback.answer()
    await state.set_state(None)
    activity = await _load(callback, api, callback_data.activity_id)
    if activity is None:
        return
    await edit_message(callback, format_habit(activity), habit_keyboard(activity.id))


@router.callback_query(HabitEditCB.filter())
async def cb_edit(
    callback: CallbackQuery,
    callback_data: HabitEditCB,
    state: FSMContext,
    api: HabitTrackerClient,
) -> None:
    """Ask for the replacement name or unit."""
    await callback.answer()
    activity = await _load(callback, api, callback_data.activity_id)
    if activity is None:
        return

    await state.update_data(
        activity_id=activity.id,
        activity_name=activity.name,
        unit=activity.unit,
    )
    if callback_data.field == "name":
        await state.set_state(HabitStates.waiting_new_name)
        ask = "Send me the new name."
    else:
        await state.set_state(HabitStates.waiting_new_unit)
        ask = (
            "Send me the new unit.\n"
            "<i>Existing entries keep their numbers — they are relabelled, not converted.</i>"
        )
    await edit_message(callback, f"{format_habit(activity)}\n\n{ask}", cancel_keyboard())


@router.message(HabitStates.waiting_new_name, _is_not_a_command)
async def on_new_name(
    message: Message,
    state: FSMContext,
    api: HabitTrackerClient,
) -> None:
    """Validate the typed name and rename the activity.

    A rejected value — too long, or already taken — leaves the state in place
    so the user can try another.
    """
    name = (message.text or "").strip()
    if not name:
        await message.answer("⚠️ Send me a name for the activity.")
        return
    if len(name) > MAX_NAME_LENGTH:
        await message.answer(f"⚠️ That's too long — keep it under {MAX_NAME_LENGTH} characters.")
        return

    data = await state.get_data()
    activity_id = data.get("activity_id")
    if not isinstance(activity_id, int):
        await state.clear()
        await message.answer(LOST)
        return

    identity = require_identity(message.from_user)
    try:
        activity = await api.update_activity(identity, activity_id=activity_id, name=name)
    except ApiError as error:
        if error.status_code == 409:
            await message.answer(f"⚠️ {escape(error.message)} Send me a different name.")
            return
        await state.clear()
        await message.answer(GONE if error.status_code == 404 else describe_api_error(error))
        return

    await state.clear()
    await message.answer(
        f"✅ Renamed {escape(str(data.get('activity_name', '')))} "
        f"to <b>{escape(activity.name)}</b>.",
        reply_markup=habit_keyboard(activity.id),
    )


@router.message(HabitStates.waiting_new_unit, _is_not_a_command)
async def on_new_unit(
    message: Message,
    state: FSMContext,
    api: HabitTrackerClient,
) -> None:
    """Validate the typed unit and apply it."""
    unit = (message.text or "").strip()
    if not unit:
        await message.answer("⚠️ Send me a unit, like km or pages.")
        return
    if len(unit) > MAX_UNIT_LENGTH:
        await message.answer(f"⚠️ That's too long — keep it under {MAX_UNIT_LENGTH} characters.")
        return

    data = await state.get_data()
    activity_id = data.get("activity_id")
    if not isinstance(activity_id, int):
        await state.clear()
        await message.answer(LOST)
        return

    identity = require_identity(message.from_user)
    try:
        activity = await api.update_activity(identity, activity_id=activity_id, unit=unit)
    except ApiError as error:
        await state.clear()
        await message.answer(GONE if error.status_code == 404 else describe_api_error(error))
        return

    await state.clear()
    await message.answer(
        f"✅ <b>{escape(activity.name)}</b> is now measured in {escape(activity.unit)}.",
        reply_markup=habit_keyboard(activity.id),
    )


@router.callback_query(HabitDeleteCB.filter(F.confirm.is_(False)))
async def cb_delete_ask(
    callback: CallbackQuery,
    callback_data: HabitDeleteCB,
    state: FSMContext,
    api: HabitTrackerClient,
) -> None:
    """Confirm before removing, stating how many entries would go too."""
    await callback.answer()
    await state.set_state(None)
    activity = await _load(callback, api, callback_data.activity_id)
    if activity is None:
        return
    await edit_message(
        callback,
        format_habit_delete_prompt(activity),
        habit_delete_confirm_keyboard(activity.id),
    )


@router.callback_query(HabitDeleteCB.filter(F.confirm.is_(True)))
async def cb_delete_confirm(
    callback: CallbackQuery,
    callback_data: HabitDeleteCB,
    api: HabitTrackerClient,
) -> None:
    """Carry the deletion out and return to the list."""
    await callback.answer()
    activity = await _load(callback, api, callback_data.activity_id)
    if activity is None:
        return

    identity = require_identity(callback.from_user)
    try:
        await api.delete_activity(identity, activity_id=activity.id)
    except ApiError as error:
        # A double tap loses the race against itself; the activity is gone
        # either way, which is the outcome the user asked for.
        if error.status_code != 404:
            await edit_message(callback, describe_api_error(error))
            return

    await _render_list(callback, api, notice=format_habit_deleted(activity))


async def _load(
    callback: CallbackQuery,
    api: HabitTrackerClient,
    activity_id: int,
) -> ActivityDetail | None:
    """Fetch one activity fresh, or redraw the screen and return ``None``.

    Keyboards from old messages stay tappable, so the id may name an activity
    that has since been renamed or deleted. Reading it again on every tap keeps
    what is shown honest and doubles as the ownership check.
    """
    identity = require_identity(callback.from_user)
    try:
        return await api.get_activity(identity, activity_id=activity_id)
    except ApiError as error:
        if error.status_code == 404:
            await _render_list(callback, api, notice=GONE)
        else:
            await edit_message(callback, describe_api_error(error))
        return None


async def _render_list(
    callback: CallbackQuery,
    api: HabitTrackerClient,
    *,
    notice: str | None = None,
) -> None:
    """Rewrite the message with the list of activities, optionally led by a notice."""
    identity = require_identity(callback.from_user)
    try:
        activities = await api.list_activities(identity)
    except ApiError as error:
        await edit_message(callback, describe_api_error(error))
        return
    body = LIST_HEADER if activities else EMPTY
    await edit_message(
        callback,
        f"{notice}\n\n{body}" if notice else body,
        habits_keyboard(activities),
    )
