from __future__ import annotations

import json
import logging

from shared.config import get_settings

logger = logging.getLogger(__name__)
_CACHE_TTL = 3600

_pool = None


def _get_pool():
    global _pool
    if _pool is None:
        import redis.asyncio as aioredis

        settings = get_settings()
        _pool = aioredis.ConnectionPool.from_url(
            settings.redis_url,
            max_connections=10,
            decode_responses=False,
        )
    return _pool


def _get_client():
    import redis.asyncio as aioredis

    return aioredis.Redis(connection_pool=_get_pool())


async def cache_get(key: str) -> list[float] | None:
    """Return cached float vector or None."""
    try:
        raw = await _get_client().get(key)
        return json.loads(raw) if raw else None
    except Exception:
        return None


async def cache_set(key: str, value: list[float], ttl: int = _CACHE_TTL) -> None:
    try:
        await _get_client().setex(key, ttl, json.dumps(value))
    except Exception:
        logger.debug("cache_set failed", exc_info=True)
