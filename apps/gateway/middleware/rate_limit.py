from __future__ import annotations

import logging
import time

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)

_WEBHOOK_PATH = "/api/v1/webhooks/"
_LIMIT = 60


def get_redis(request: Request):
    return request.app.state.redis


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if not request.url.path.startswith(_WEBHOOK_PATH):
            return await call_next(request)

        installation_id = request.headers.get("X-GitHub-Hook-Installation-Target-ID") or request.headers.get("X-Installation-Id", "unknown")
        minute_bucket = int(time.time()) // 60
        key = f"rate:{installation_id}:{minute_bucket}"

        try:
            redis = get_redis(request)
            count = await redis.incr(key)
            if count == 1:
                await redis.expire(key, 120)
        except Exception:
            logger.warning("Rate limit Redis unavailable — allowing request", exc_info=True)
            return await call_next(request)

        if count > _LIMIT:
            return Response(
                status_code=429,
                content='{"detail":"Rate limit exceeded"}',
                media_type="application/json",
                headers={"Retry-After": "60"},
            )

        return await call_next(request)
