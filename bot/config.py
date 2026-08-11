"""Bot configuration loaded from environment variables."""

from decimal import Decimal
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class BotSettings(BaseSettings):
    """Runtime settings, populated from the environment or a local ``.env``."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    telegram_bot_token: str
    # Service name inside the compose network; override to localhost on the host.
    api_url: str = "http://api:8000"
    internal_api_key: str

    request_timeout: float = 10.0

    summary_days: int = 7
    summary_alt_days: int = 30

    amount_presets: tuple[Decimal, ...] = (
        Decimal("1"),
        Decimal("2"),
        Decimal("5"),
        Decimal("10"),
        Decimal("30"),
    )


@lru_cache
def get_settings() -> BotSettings:
    """Return the process-wide settings singleton."""
    return BotSettings()


settings: BotSettings = get_settings()
