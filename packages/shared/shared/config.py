from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings

_REQUIRED_NON_EMPTY = ("github_webhook_secret", "github_app_id", "github_private_key_b64", "github_client_id", "github_client_secret", "jwt_secret_key")


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

    @field_validator(*_REQUIRED_NON_EMPTY, mode="before")
    @classmethod
    def _reject_blank(cls, v: str, info) -> str:
        if not v or not v.strip():
            raise ValueError(f"{info.field_name} must not be blank")
        return v

    # App
    env: str = "development"
    api_prefix: str = "/api/v1"
    anthropic_api_key: str | None = None
    gemini_api_key: str | None = None
    public_url: str | None = None  # e.g. https://xxx.ngrok-free.app — enables dashboard links in PR comments


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore
