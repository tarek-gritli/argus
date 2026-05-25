from __future__ import annotations

import secrets
import urllib.parse

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse
from integrations.oauth import notion as notion_oauth
from integrations.oauth import slack as slack_oauth
from shared.config import get_settings
from shared.crypto import encrypt
from shared.db import session_context
from shared.models.org_integration import OrgIntegration

router = APIRouter()


async def _store_state(request: Request, key: str, org_id: str) -> None:
    await request.app.state.redis.setex(key, 600, org_id)


async def _pop_state(request: Request, key: str) -> str | None:
    val = await request.app.state.redis.getdel(key)
    return val if val else None


async def _save_integration(org_id: str, kind: str, config: dict) -> None:
    async with session_context() as session:
        integration = OrgIntegration(org_id=org_id, kind=kind, config=config)
        session.add(integration)
        await session.commit()


async def _exchange_slack_code(code: str, redirect_uri: str) -> dict:
    settings = get_settings()
    return await slack_oauth.exchange_code(code, settings.slack_client_id, settings.slack_client_secret, redirect_uri)


async def _exchange_notion_code(code: str, redirect_uri: str) -> dict:
    settings = get_settings()
    return await notion_oauth.exchange_code(code, settings.notion_client_id, settings.notion_client_secret, redirect_uri)


@router.get("/slack/authorize")
async def slack_authorize(org_id: str, request: Request):
    settings = get_settings()
    nonce = secrets.token_urlsafe(16)
    await _store_state(request, f"oauth:slack:{nonce}", org_id)
    redirect_uri = f"{settings.app_base_url}/api/v1/oauth/slack/callback"
    params = urllib.parse.urlencode(
        {
            "client_id": settings.slack_client_id,
            "scope": slack_oauth.SCOPES,
            "redirect_uri": redirect_uri,
            "state": nonce,
        }
    )
    return RedirectResponse(f"{slack_oauth.AUTHORIZE_URL}?{params}", status_code=302)


@router.get("/slack/callback")
async def slack_callback(code: str, state: str, request: Request):
    settings = get_settings()
    org_id = await _pop_state(request, f"oauth:slack:{state}")
    if not org_id:
        raise HTTPException(status_code=400, detail="Invalid or expired OAuth state")
    redirect_uri = f"{settings.app_base_url}/api/v1/oauth/slack/callback"
    try:
        data = await _exchange_slack_code(code, redirect_uri)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    webhook = data.get("incoming_webhook", {})
    config = {
        "token": encrypt(data["access_token"]),
        "channel": webhook.get("channel", ""),
        "webhook_url": encrypt(webhook.get("url", "")),
    }
    await _save_integration(org_id, "slack", config)
    return {"status": "connected"}


@router.get("/notion/authorize")
async def notion_authorize(org_id: str, request: Request):
    settings = get_settings()
    nonce = secrets.token_urlsafe(16)
    await _store_state(request, f"oauth:notion:{nonce}", org_id)
    redirect_uri = f"{settings.app_base_url}/api/v1/oauth/notion/callback"
    params = urllib.parse.urlencode(
        {
            "client_id": settings.notion_client_id,
            "response_type": "code",
            "owner": "user",
            "redirect_uri": redirect_uri,
            "state": nonce,
        }
    )
    return RedirectResponse(f"{notion_oauth.AUTHORIZE_URL}?{params}", status_code=302)


@router.get("/notion/callback")
async def notion_callback(code: str, state: str, request: Request):
    settings = get_settings()
    org_id = await _pop_state(request, f"oauth:notion:{state}")
    if not org_id:
        raise HTTPException(status_code=400, detail="Invalid or expired OAuth state")
    redirect_uri = f"{settings.app_base_url}/api/v1/oauth/notion/callback"
    try:
        data = await _exchange_notion_code(code, redirect_uri)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail="Notion token exchange failed") from exc
    config = {
        "token": encrypt(data["access_token"]),
        "workspace_id": data.get("workspace_id", ""),
    }
    await _save_integration(org_id, "notion", config)
    return {"status": "connected"}
