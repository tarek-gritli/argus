from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Infrastructure
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/1"
    database_url: str = "postgresql+asyncpg://argus:argus@localhost:5432/argus"

    # GitHub App
    github_webhook_secret: str
    github_app_id: str
    github_private_key_b64: str

    # Auth
    github_client_id: str
    github_client_secret: str
    jwt_secret_key: str
    jwt_ttl_seconds: int = 86400

    # App
    env: str = "development"
    api_prefix: str = "/api/v1"
    anthropic_api_key: str | None = None


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore
