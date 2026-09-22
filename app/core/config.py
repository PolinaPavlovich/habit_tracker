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

    # Needed to verify Mini App ``initData`` signatures. No default, for the
    # same reason as the key above. The API process already loads this token
    # transitively — ``app.main`` imports ``bot.webhook``, which builds a Bot at
    # import time — but sourcing an API secret through the bot's settings class
    # is an accident waiting to be untangled, so it is declared here too.
    telegram_bot_token: str

    # How long a signed ``initData`` payload stays acceptable. Telegram does not
    # expire these itself, so this bounds how long a captured payload is useful.
    init_data_max_age_seconds: int = 86400

    # Signs the JWTs handed to a TV after a QR approval. Separate from
    # ``internal_api_key`` on purpose: different blast radius, and it must be
    # rotatable — rotation is the only way to revoke issued tokens — without
    # redeploying the bot. No default, like every other secret here.
    jwt_secret: str
    jwt_ttl_seconds: int = 30 * 24 * 60 * 60

    # How long an unapproved QR session stays scannable.
    qr_session_ttl_seconds: int = 120
    # Used to build the t.me deep link encoded in the QR image.
    telegram_bot_username: str = ""

    # Browser origins allowed to call this API, comma separated. A list field
    # would force JSON syntax in ``.env``; a plain string keeps the file
    # readable. Never widen this to "*": the SPA sends an Authorization header,
    # so every request preflights and a wildcard would let any site replay it.
    cors_origins: str = ""

    @computed_field  # type: ignore[prop-decorator]
    @property
    def cors_origin_list(self) -> list[str]:
        """Allowed origins, split and trimmed."""
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

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
