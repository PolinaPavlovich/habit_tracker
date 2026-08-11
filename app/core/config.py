"""Application configuration loaded from environment variables."""

from functools import lru_cache

from pydantic import computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings, populated from the environment or a local ``.env``."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Habit Tracker API"
    app_env: str = "local"

    postgres_user: str = "postgres"
    postgres_password: str = "postgres"
    postgres_db: str = "habit_tracker"
    postgres_host: str = "localhost"
    postgres_port: int = 5432

    summary_window_days: int = 7

    # Shared secret the Telegram bot presents on every call. Deliberately has no
    # default: the API must refuse to boot rather than run unauthenticated.
    internal_api_key: str

    @computed_field  # type: ignore[prop-decorator]
    @property
    def database_url(self) -> str:
        """Async SQLAlchemy DSN used by the application engine."""
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


@lru_cache
def get_settings() -> Settings:
    """Return the process-wide settings singleton."""
    return Settings()


settings: Settings = get_settings()
