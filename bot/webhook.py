from fastapi import APIRouter, Request
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import Update
from aiogram.fsm.storage.memory import MemoryStorage

# Замени импорты на свои актуальные
from bot.config import settings
from bot.client import HabitTrackerClient
from bot.handlers import ROUTERS

bot = Bot(
    token=settings.telegram_bot_token,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML),
)

# Инициализируем диспетчер
dispatcher = Dispatcher(storage=MemoryStorage())
dispatcher.include_routers(*ROUTERS)

# Создаем твой API-клиент
api = HabitTrackerClient(
    base_url=settings.api_url,
    api_key=settings.internal_api_key,
    timeout=settings.request_timeout,
)
dispatcher["api"] = api

router = APIRouter(tags=["telegram"])

@router.post("/webhook")
async def telegram_webhook(request: Request):
    """Принимает обновления от Telegram и передает их в aiogram."""
    webhook_data = await request.json()
    update = Update.model_validate(webhook_data, context={"bot": bot})
    
    # Передаем апдейт в aiogram
    await dispatcher.feed_update(bot=bot, update=update)
    return {"status": "ok"}