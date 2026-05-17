"""Application configuration via pydantic-settings — all values from env vars."""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central configuration — every secret comes from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── App ──
    app_name: str = "FinanceApp"
    app_env: str = "development"
    app_version: str = "1.0.0"
    log_level: str = "INFO"
    allowed_origins: str = "http://localhost:3000,http://localhost:8080"

    # ── Database ──
    database_url: str = "postgresql+asyncpg://financeapp:financeapp_dev@localhost:5432/financeapp"
    database_url_sync: str = "postgresql://financeapp:financeapp_dev@localhost:5432/financeapp"

    # ── Redis ──
    redis_url: str = "redis://localhost:6379/0"

    # ── ClickHouse ──
    clickhouse_url: str = "http://localhost:8123"

    # ── Auth ──
    secret_key: str = "change-me-to-a-random-string-min-32-chars-long"
    field_encryption_key: str = "change-me-to-a-fernet-key"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7
    bcrypt_rounds: int = 12

    # ── AI Providers ──
    groq_api_key: str = ""
    gemini_api_key: str = ""
    ollama_url: str = "http://localhost:11434"

    # ── Celery ──
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"

    # ── Email ──
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_pass: str = ""

    # ── Business Logic ──
    safety_buffer_usd: int = 500

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def origins_list(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    """Cached settings singleton."""
    return Settings()
