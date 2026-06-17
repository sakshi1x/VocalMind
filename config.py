"""Application configuration."""
import os
import logging
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    DATABASE_URL: str
    REDIS_URL: str = "redis://redis:6379/0"
    AUTH_CACHE_TTL_SECONDS: int = 300

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        extra="ignore"
    )

    @property
    def async_database_url(self) -> str:
        """Return a SQLAlchemy async-compatible database URL."""
        url = self.DATABASE_URL

        if url.startswith("postgres://"):
            return "postgresql+asyncpg://" + url.split("://", 1)[1]

        if url.startswith("postgresql://") and "+asyncpg" not in url:
            return url.replace(
                "postgresql://",
                "postgresql+asyncpg://",
                1
            )

        return url


settings = Settings()