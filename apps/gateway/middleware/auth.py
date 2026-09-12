from __future__ import annotations

import logging

import jwt
from fastapi import Request, Response
from shared.config import get_settings
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)

_EXEMPT_EXACT = frozenset(["/ping"])


def _build_exempt_prefixes() -> tuple[str, ...]:
    p = get_settings().api_prefix
    return (
        f"{p}/webhooks/",
        f"{p}/auth/github/",
        f"{p}/auth/logout",
        f"{p}/auth/cli/",
        f"{p}/auth/validate-nonce",
        "/dashboard/",
        # OAuth callbacks come from third-party redirects — no auth token present
        f"{p}/oauth/slack/callback",
        f"{p}/oauth/notion/callback",
        f"{p}/oauth/linear/callback",
        f"{p}/oauth/jira/callback",
    )


class AuthMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        self._exempt = _build_exempt_prefixes()

    async def dispatch(self, request: Request, call_next):
        if request.method == "OPTIONS":
            return await call_next(request)
        path = request.url.path
        if path in _EXEMPT_EXACT or any(path.startswith(p) for p in self._exempt):
            return await call_next(request)

        token = _extract_token(request)
        if not token:
            logger.warning("No token found for %s", path)
            return Response(status_code=401, content='{"detail":"Unauthorized"}', media_type="application/json")

        try:
            settings = get_settings()
            payload = jwt.decode(token, settings.jwt_secret_key, algorithms=["HS256"])
        except jwt.PyJWTError as e:
            logger.warning("JWT validation failed for %s: %s", path, e)
            return Response(status_code=401, content='{"detail":"Unauthorized"}', media_type="application/json")

        try:
            request.state.user_id = payload["sub"]
            request.state.org_id = payload["oid"]
            request.state.role = payload["role"]
        except KeyError:
            return Response(status_code=401, content='{"detail":"Unauthorized"}', media_type="application/json")
        return await call_next(request)


def _extract_token(request: Request) -> str | None:
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        return auth[7:]
    return request.cookies.get("argus_token")
