"""Bot entrypoint: wire up the dispatcher and poll Telegram."""

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand

from bot.client import HabitTrackerClient
from bot.config import settings
from bot.handlers import ROUTERS

logger = logging.getLogger(__name__)

COMMANDS: tuple[BotCommand, ...] = (
    BotCommand(command="log", description="Record an activity"),
    BotCommand(command="summary", description="Totals for the last few days"),
    BotCommand(command="new", description="Add a new activity"),
    BotCommand(command="cancel", description="Abandon the current step"),
)


async def main() -> None:
    """Run the bot until interrupted."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    bot = Bot(
        token=settings.telegram_bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dispatcher = Dispatcher(storage=MemoryStorage())
    dispatcher.include_routers(*ROUTERS)

    # One client for the whole process, so connections are pooled. aiogram
    # passes matching workflow-data keys to handlers as keyword arguments,
    # which is how handlers receive ``api``.
    api = HabitTrackerClient(
        base_url=settings.api_url,
        api_key=settings.internal_api_key,
        timeout=settings.request_timeout,
    )
    dispatcher["api"] = api

    try:
        await bot.set_my_commands(list(COMMANDS))
        logger.info("Polling Telegram, backend at %s", settings.api_url)
        # Polling, not webhooks: no public URL or TLS termination needed.
        await dispatcher.start_polling(bot)
    finally:
        await api.aclose()
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped.")
