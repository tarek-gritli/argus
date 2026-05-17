from __future__ import annotations

import logging
from pathlib import Path

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)

_WEBHOOK_PATH = "/api/v1/webhooks/"
_CAPACITY = 60
_REFILL_RATE = 1
_TTL = 120

_LUA_SCRIPT = (Path(__file__).parent / "token_bucket.lua").read_text()


def get_redis(request: Request):
    return request.app.state.redis


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, **kwargs):
        super().__init__(app, **kwargs)
        self._sha: str | None = None

    async def _get_sha(self, redis) -> str:
        if self._sha is None:
            self._sha = str(await redis.script_load(_LUA_SCRIPT))
        return self._sha

    async def dispatch(self, request: Request, call_next):
        if not request.url.path.startswith(_WEBHOOK_PATH):
            return await call_next(request)

        installation_id = request.headers.get("X-GitHub-Hook-Installation-Target-ID") or request.headers.get("X-Installation-Id", "unknown")
        key = f"tb:{installation_id}"

        try:
            redis = get_redis(request)
            sha = await self._get_sha(redis)
            try:
                result = await redis.evalsha(sha, 1, key, _CAPACITY, _REFILL_RATE, _TTL)
            except Exception as e:
                if "NOSCRIPT" in str(e):
                    self._sha = None
                    sha = await self._get_sha(redis)
                    result = await redis.evalsha(sha, 1, key, _CAPACITY, _REFILL_RATE, _TTL)
                else:
                    raise
            allowed = result[0]
        except Exception:
            logger.warning("Rate limit Redis unavailable — allowing request", exc_info=True)
            return await call_next(request)

        if not allowed:
            return Response(
                status_code=429,
                content='{"detail":"Rate limit exceeded"}',
                media_type="application/json",
                headers={"Retry-After": "1"},
            )

        return await call_next(request)
