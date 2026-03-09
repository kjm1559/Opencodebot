"""Configuration management using Pydantic Settings."""

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    class Config:
        env_file = ".env"
        case_sensitive = False

    # PostgreSQL Configuration
    postgres_user: str
    postgres_password: str
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "stocknews"

    @property
    def database_url(self) -> str:
        """Return PostgreSQL async connection URL."""
        return f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"

    # Redis Configuration
    redis_url: str = "redis://localhost:6379/0"

    # Celery Configuration
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/0"

    # API Keys
    finnhub_api_key: str
    alphavantage_api_key: str = ""
    gnews_api_key: str = ""

    # FastAPI Configuration
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    app_debug: bool = False


@lru_cache
def get_settings() -> Settings:
    """Return cached Settings instance (singleton pattern)."""
    return Settings()
