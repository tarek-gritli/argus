from __future__ import annotations

import redis as redis_lib
from shared.config import get_settings

redis_client: redis_lib.Redis | None = None


def init_connections() -> None:
    global redis_client
    settings = get_settings()
    redis_client = redis_lib.Redis.from_url(settings.redis_url, decode_responses=True)


def close_connections() -> None:
    global redis_client
    if redis_client:
        redis_client.close()
        redis_client = None
