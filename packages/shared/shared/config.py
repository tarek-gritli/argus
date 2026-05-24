from functools import lru_cache

from cryptography.fernet import Fernet
from pydantic import field_validator
from pydantic_settings import BaseSettings

_REQUIRED_NON_EMPTY = ("github_webhook_secret", "github_app_id", "github_private_key_b64", "github_client_id", "github_client_secret", "jwt_secret_key", "secret_encryption_key")


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

    # Encryption
    secret_encryption_key: str

    # Context / vector store
    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: str = ""
    qdrant_embedding_dim: int = 1024

    # Voyage AI
    voyage_api_key: str | None = None

    # Slack OAuth
    slack_client_id: str = ""
    slack_client_secret: str = ""

    # Notion OAuth
    notion_client_id: str = ""
    notion_client_secret: str = ""

    # Linear OAuth
    linear_client_id: str = ""
    linear_client_secret: str = ""

    # Jira OAuth
    jira_client_id: str = ""
    jira_client_secret: str = ""

    # App
    env: str = "development"
    api_prefix: str = "/api/v1"
    anthropic_api_key: str | None = None
    gemini_api_key: str | None = None
    app_base_url: str = "http://localhost:8000"

    @field_validator(*_REQUIRED_NON_EMPTY, mode="before")
    @classmethod
    def _reject_blank(cls, v: str, info) -> str:
        if not v or not v.strip():
            raise ValueError(f"{info.field_name} must not be blank")
        return v

    @field_validator("secret_encryption_key", mode="after")
    @classmethod
    def _validate_fernet_key(cls, v: str) -> str:
        try:
            Fernet(v.encode())
        except Exception as exc:
            raise ValueError("secret_encryption_key is not a valid Fernet key") from exc
        return v

    # Stripe
    stripe_secret_key: str | None = None
    stripe_webhook_secret: str | None = None
    stripe_pro_price_id: str | None = None
    stripe_team_price_id: str | None = None
    stripe_success_url: str = "http://localhost:3000/billing/success"
    stripe_cancel_url: str = "http://localhost:3000/billing/cancel"


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore
