from __future__ import annotations

import secrets

from fastapi import APIRouter, Request, Response
from shared.config import get_settings

router = APIRouter()
_SESSION_TTL = 300  # 5 minutes


@router.post("/session")
async def create_cli_session(request: Request):
    session_id = secrets.token_urlsafe(32)
    await request.app.state.redis.set(f"cli_session:{session_id}", "", ex=_SESSION_TTL)
    settings = get_settings()
    browser_url = f"{settings.app_base_url}{settings.api_prefix}/auth/github/login?cli_session_id={session_id}"
    return {"session_id": session_id, "browser_url": browser_url}


@router.get("/token/{session_id}")
async def poll_cli_token(session_id: str, request: Request):
    value = await request.app.state.redis.get(f"cli_session:{session_id}")
    if value is None or value == "" or value == b"":
        return Response(status_code=202)
    await request.app.state.redis.delete(f"cli_session:{session_id}")
    token = value.decode() if isinstance(value, bytes) else value
    return {"token": token}
