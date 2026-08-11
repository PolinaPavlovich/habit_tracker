"""The ``/log`` flow: pick an activity, pick or type an amount, record it."""

from decimal import Decimal

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.client import ApiError, HabitTrackerClient
from bot.config import settings
from bot.formatting import describe_api_error, format_log_confirmation, parse_amount
from bot.handlers.common import edit_message
from bot.identity import Identity, require_identity
from bot.keyboards import (
    CUSTOM_AMOUNT,
    ActivityCB,
    AmountCB,
    NavCB,
    activities_keyboard,
    amounts_keyboard,
    cancel_keyboard,
)
from bot.schemas import Activity
from bot.states import LogStates

router = Router(name="log")

PICK_ACTIVITY = "What did you do?"
NO_ACTIVITIES = "You don't have any activities yet. Add one to get started:"


@router.message(Command("log"))
async def cmd_log(
    message: Message,
    state: FSMContext,
    api: HabitTrackerClient,
) -> None:
    """Open the flow with the user's activity list."""
    await state.clear()
    identity = require_identity(message.from_user)
    try:
        activities = await api.list_activities(identity)
    except ApiError as error:
        await message.answer(describe_api_error(error))
        return

    await _remember(state, activities)
    text = PICK_ACTIVITY if activities else NO_ACTIVITIES
    await message.answer(text, reply_markup=activities_keyboard(activities))


@router.callback_query(NavCB.filter(F.action == "back"))
async def cb_back(
    callback: CallbackQuery,
    state: FSMContext,
    api: HabitTrackerClient,
) -> None:
    """Return to the activity list from the amount step."""
    await callback.answer()
    await state.set_state(None)
    identity = require_identity(callback.from_user)
    try:
        activities = await api.list_activities(identity)
    except ApiError as error:
        await edit_message(callback, describe_api_error(error))
        return

    await _remember(state, activities)
    text = PICK_ACTIVITY if activities else NO_ACTIVITIES
    await edit_message(callback, text, activities_keyboard(activities))


@router.callback_query(ActivityCB.filter())
async def cb_pick_activity(
    callback: CallbackQuery,
    callback_data: ActivityCB,
    state: FSMContext,
    api: HabitTrackerClient,
) -> None:
    """Offer preset amounts for the chosen activity."""
    await callback.answer()
    identity = require_identity(callback.from_user)
    activity = await _resolve(state, api, identity, callback_data.activity_id)
    if activity is None:
        await edit_message(callback, "⚠️ That activity is gone. Send /log to start over.")
        return

    await state.update_data(activity_id=activity.id)
    await edit_message(
        callback,
        f"How much? ({activity.unit})",
        amounts_keyboard(activity.id, settings.amount_presets),
    )


@router.callback_query(AmountCB.filter())
async def cb_pick_amount(
    callback: CallbackQuery,
    callback_data: AmountCB,
    state: FSMContext,
    api: HabitTrackerClient,
) -> None:
    """Record a preset amount, or switch to waiting for a typed one."""
    await callback.answer()
    identity = require_identity(callback.from_user)
    activity = await _resolve(state, api, identity, callback_data.activity_id)
    if activity is None:
        await edit_message(callback, "⚠️ That activity is gone. Send /log to start over.")
        return

    if callback_data.value == CUSTOM_AMOUNT:
        await state.set_state(LogStates.waiting_amount)
        await state.update_data(activity_id=activity.id)
        await edit_message(
            callback,
            f"How much {activity.unit} of {activity.name}? Send me a number.",
            cancel_keyboard(),
        )
        return

    text = await _submit(api, identity, activity, Decimal(callback_data.value))
    await state.set_state(None)
    await edit_message(callback, text)


@router.message(LogStates.waiting_amount)
async def on_typed_amount(
    message: Message,
    state: FSMContext,
    api: HabitTrackerClient,
) -> None:
    """Validate the typed amount and record it.

    A rejected value leaves the state in place so the user can simply try again.
    """
    try:
        amount = parse_amount(message.text or "")
    except ValueError as error:
        await message.answer(f"⚠️ {error}")
        return

    data = await state.get_data()
    activity_id = data.get("activity_id")
    if not isinstance(activity_id, int):
        await state.clear()
        await message.answer("⚠️ I lost track of that one. Send /log to start over.")
        return

    identity = require_identity(message.from_user)
    activity = await _resolve(state, api, identity, activity_id)
    if activity is None:
        await state.clear()
        await message.answer("⚠️ That activity is gone. Send /log to start over.")
        return

    text = await _submit(api, identity, activity, amount)
    await state.set_state(None)
    await message.answer(text)


async def _submit(
    api: HabitTrackerClient,
    identity: Identity,
    activity: Activity,
    amount: Decimal,
) -> str:
    """Post the entry and return the message to show for the outcome."""
    try:
        await api.create_log(identity, activity_id=activity.id, amount=amount)
    except ApiError as error:
        return describe_api_error(error)
    return format_log_confirmation(activity.name, activity.unit, amount)


async def _remember(state: FSMContext, activities: list[Activity]) -> None:
    """Cache the activity list in FSM state.

    The API exposes no ``GET /activities/{id}``, so caching the list when it is
    rendered saves a round trip on every subsequent step of the flow.
    """
    await state.update_data(
        activities={
            str(activity.id): {"name": activity.name, "unit": activity.unit}
            for activity in activities
        }
    )


async def _resolve(
    state: FSMContext,
    api: HabitTrackerClient,
    identity: Identity,
    activity_id: int,
) -> Activity | None:
    """Look the activity up in the cache, refetching if the state has been lost.

    Returns ``None`` when it no longer exists — or never belonged to this user,
    since the API reports both the same way.
    """
    data = await state.get_data()
    cached = data.get("activities")
    if isinstance(cached, dict):
        entry = cached.get(str(activity_id))
        if isinstance(entry, dict):
            return Activity(id=activity_id, name=entry["name"], unit=entry["unit"])

    try:
        activities = await api.list_activities(identity)
    except ApiError:
        return None
    await _remember(state, activities)
    return next((item for item in activities if item.id == activity_id), None)
