"""Entry-point commands and helpers shared by the other handler modules."""

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message

from bot.keyboards import NavCB

router = Router(name="common")

HELP_TEXT = (
    "I keep your habit journal.\n\n"
    "/log — record an activity\n"
    "/summary — totals for the last few days\n"
    "/new — add a new activity\n"
    "/cancel — abandon what we were doing"
)


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext) -> None:
    """Greet the user and clear anything left over from a previous flow."""
    await state.clear()
    await message.answer(f"👋 Hi!\n\n{HELP_TEXT}")


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    """Show the command list."""
    await message.answer(HELP_TEXT)


@router.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext) -> None:
    """Drop out of any multi-step flow.

    Registered on the first router so it wins over the state-bound message
    handlers that would otherwise swallow the command as free text.
    """
    await state.clear()
    await message.answer("Okay, cancelled. /log when you're ready.")


@router.callback_query(NavCB.filter(F.action == "cancel"))
async def cb_cancel(callback: CallbackQuery, state: FSMContext) -> None:
    """Same, from the inline button offered while we wait for typed input."""
    await callback.answer()
    await state.clear()
    await edit_message(callback, "Okay, cancelled. /log when you're ready.")


async def edit_message(
    callback: CallbackQuery,
    text: str,
    reply_markup: InlineKeyboardMarkup | None = None,
) -> None:
    """Rewrite the message the button belongs to, keeping the chat tidy.

    ``callback.message`` is absent for messages Telegram no longer lets bots
    touch (too old, or deleted), in which case there is nothing to edit and the
    reply is sent fresh instead.
    """
    if isinstance(callback.message, Message):
        await callback.message.edit_text(text, reply_markup=reply_markup)
    elif callback.bot is not None and callback.message is not None:
        await callback.bot.send_message(
            callback.message.chat.id,
            text,
            reply_markup=reply_markup,
        )
