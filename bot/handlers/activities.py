"""The ``/new`` flow: create an activity by naming it and giving it a unit."""

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.client import ApiError, HabitTrackerClient
from bot.formatting import describe_api_error
from bot.handlers.common import edit_message
from bot.identity import require_identity
from bot.keyboards import NavCB, cancel_keyboard
from bot.states import ActivityStates

router = Router(name="activities")

# Mirrors the API's ActivityCreate constraints.
MAX_NAME_LENGTH = 100
MAX_UNIT_LENGTH = 32

ASK_NAME = "What should I call it? (e.g. Running)"
ASK_UNIT = "And the unit you measure it in? (e.g. km)"


@router.message(Command("new"))
async def cmd_new(message: Message, state: FSMContext) -> None:
    """Start the flow from the command."""
    await state.clear()
    await state.set_state(ActivityStates.waiting_name)
    await message.answer(ASK_NAME, reply_markup=cancel_keyboard())


@router.callback_query(NavCB.filter(F.action == "new"))
async def cb_new(callback: CallbackQuery, state: FSMContext) -> None:
    """Start the same flow from the button on the activity list."""
    await callback.answer()
    await state.clear()
    await state.set_state(ActivityStates.waiting_name)
    await edit_message(callback, ASK_NAME, cancel_keyboard())


@router.message(ActivityStates.waiting_name)
async def on_name(message: Message, state: FSMContext) -> None:
    """Accept the name and ask for the unit."""
    name = (message.text or "").strip()
    if not name:
        await message.answer("⚠️ Send me a name for the activity.")
        return
    if len(name) > MAX_NAME_LENGTH:
        await message.answer(
            f"⚠️ That's too long — keep it under {MAX_NAME_LENGTH} characters."
        )
        return

    await state.update_data(name=name)
    await state.set_state(ActivityStates.waiting_unit)
    await message.answer(ASK_UNIT, reply_markup=cancel_keyboard())


@router.message(ActivityStates.waiting_unit)
async def on_unit(
    message: Message,
    state: FSMContext,
    api: HabitTrackerClient,
) -> None:
    """Accept the unit and create the activity."""
    unit = (message.text or "").strip()
    if not unit:
        await message.answer("⚠️ Send me a unit, like km or pages.")
        return
    if len(unit) > MAX_UNIT_LENGTH:
        await message.answer(
            f"⚠️ That's too long — keep it under {MAX_UNIT_LENGTH} characters."
        )
        return

    data = await state.get_data()
    name = data.get("name")
    if not isinstance(name, str):
        await state.clear()
        await message.answer("⚠️ I lost track of that one. Send /new to start over.")
        return

    identity = require_identity(message.from_user)
    try:
        activity = await api.create_activity(identity, name=name, unit=unit)
    except ApiError as error:
        await state.clear()
        await message.answer(describe_api_error(error))
        return

    await state.clear()
    await message.answer(
        f"✅ Added <b>{activity.name}</b> measured in {activity.unit}. Send /log to record some."
    )
