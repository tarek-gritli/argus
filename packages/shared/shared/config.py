from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/1"

    # Github
    github_webhook_secret: str
    github_app_id: str
    github_app_private_key: str

    # Environment
    env: str = "development"


settings = Settings()  # type: ignore
