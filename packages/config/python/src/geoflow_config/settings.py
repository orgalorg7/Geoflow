from functools import lru_cache

from pydantic import AnyHttpUrl
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    app_name: str = "GeoFlow API"
    app_version: str = "0.1.0"
    environment: str = "development"
    log_level: str = "INFO"

    database_url: str = (
        "postgresql+asyncpg://geoflow:change-me-in-production@localhost:5432/geoflow"
    )
    alembic_database_url: str = (
        "postgresql+psycopg://geoflow:change-me-in-production@localhost:5432/geoflow"
    )
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"

    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_cors_origins: list[AnyHttpUrl] = [AnyHttpUrl("http://localhost:3000")]

    auth_secret_key: str = "development-only-change-this-secret-before-deployment"
    auth_access_token_minutes: int = 15
    auth_refresh_token_days: int = 7
    auth_cookie_secure: bool = False
    auth_cookie_domain: str | None = None
    auth_access_cookie_name: str = "geoflow_access"
    auth_refresh_cookie_name: str = "geoflow_refresh"


@lru_cache
def get_settings() -> Settings:
    return Settings()
