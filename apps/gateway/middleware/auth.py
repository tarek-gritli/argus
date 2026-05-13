from __future__ import annotations

import jwt
from fastapi import Request, Response
from shared.config import get_settings
from starlette.middleware.base import BaseHTTPMiddleware

_EXEMPT_PREFIXES = ("/ping", "/api/v1/webhooks/", "/api/v1/auth/github/", "/api/v1/admin/")


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if any(path.startswith(p) for p in _EXEMPT_PREFIXES):
            return await call_next(request)

        token = _extract_token(request)
        if not token:
            return Response(status_code=401, content='{"detail":"Unauthorized"}', media_type="application/json")

        try:
            settings = get_settings()
            payload = jwt.decode(token, settings.jwt_secret_key, algorithms=["HS256"])
        except jwt.PyJWTError:
            return Response(status_code=401, content='{"detail":"Unauthorized"}', media_type="application/json")

        request.state.user_id = payload["sub"]
        request.state.org_id = payload["oid"]
        request.state.role = payload["role"]
        return await call_next(request)


def _extract_token(request: Request) -> str | None:
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        return auth[7:]
    return request.cookies.get("argus_token")
