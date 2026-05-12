from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/1"

    # Github
    github_webhook_secret: str
    github_app_id: str
    github_private_key_b64: str

    # Gitlab
    gitlab_webhook_secret: str
    gitlab_bot_user_id: str
    gitlab_access_token: str
    gitlab_signing_token: str

    # Environment
    env: str = "development"

    # API
    api_prefix: str = "/api/v1"

    # LLM
    anthropic_api_key: str | None = None


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore
