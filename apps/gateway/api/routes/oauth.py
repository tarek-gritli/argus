from __future__ import annotations

import secrets
import urllib.parse

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from integrations.oauth import jira as jira_oauth
from integrations.oauth import linear as linear_oauth
from integrations.oauth import notion as notion_oauth
from integrations.oauth import slack as slack_oauth
from shared.config import get_settings
from shared.crypto import encrypt
from shared.db import session_context
from shared.models.org_integration import OrgIntegration

router = APIRouter()


def _get_org_id(request: Request) -> str:
    return request.state.org_id


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


async def _exchange_linear_code(code: str, redirect_uri: str) -> dict:
    settings = get_settings()
    return await linear_oauth.exchange_code(code, settings.linear_client_id, settings.linear_client_secret, redirect_uri)


async def _exchange_jira_code(code: str, redirect_uri: str) -> dict:
    settings = get_settings()
    data = await jira_oauth.exchange_code(code, settings.jira_client_id, settings.jira_client_secret, redirect_uri)
    resources = await jira_oauth.get_accessible_resources(data["access_token"])
    if not resources or not resources[0].get("id"):
        raise ValueError("No accessible Jira cloud resource found for this token")
    site = resources[0]
    cloud_id = site["id"]
    data["cloud_id"] = cloud_id
    data["site_url"] = site.get("url", "")
    data["base_url"] = f"https://api.atlassian.com/ex/jira/{cloud_id}"
    return data


@router.get("/slack/authorize")
async def slack_authorize(org_id: str, request: Request, org_id_from_token: str = Depends(_get_org_id)):
    if org_id_from_token != org_id:
        raise HTTPException(status_code=403, detail="Forbidden")
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
    except Exception as exc:
        raise HTTPException(status_code=502, detail="Slack token exchange failed") from exc
    webhook = data.get("incoming_webhook", {})
    config = {
        "channel": webhook.get("channel", ""),
        "webhook_url": encrypt(webhook.get("url", "")),
    }
    await _save_integration(org_id, "slack", config)
    return RedirectResponse(url=f"{get_settings().frontend_url}/dashboard/integrations", status_code=302)


@router.get("/notion/authorize")
async def notion_authorize(org_id: str, request: Request, org_id_from_token: str = Depends(_get_org_id)):
    if org_id_from_token != org_id:
        raise HTTPException(status_code=403, detail="Forbidden")
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
    return RedirectResponse(url=f"{get_settings().frontend_url}/dashboard/integrations", status_code=302)


@router.get("/linear/authorize")
async def linear_authorize(org_id: str, request: Request, org_id_from_token: str = Depends(_get_org_id)):
    if org_id_from_token != org_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    settings = get_settings()
    nonce = secrets.token_urlsafe(16)
    await _store_state(request, f"oauth:linear:{nonce}", org_id)
    redirect_uri = f"{settings.app_base_url}/api/v1/oauth/linear/callback"
    params = urllib.parse.urlencode(
        {
            "client_id": settings.linear_client_id,
            "response_type": "code",
            "scope": linear_oauth.SCOPES,
            "redirect_uri": redirect_uri,
            "state": nonce,
        }
    )
    return RedirectResponse(f"{linear_oauth.AUTHORIZE_URL}?{params}", status_code=302)


@router.get("/linear/callback")
async def linear_callback(code: str, state: str, request: Request):
    settings = get_settings()
    org_id = await _pop_state(request, f"oauth:linear:{state}")
    if not org_id:
        raise HTTPException(status_code=400, detail="Invalid or expired OAuth state")
    redirect_uri = f"{settings.app_base_url}/api/v1/oauth/linear/callback"
    try:
        data = await _exchange_linear_code(code, redirect_uri)
    except Exception as exc:
        raise HTTPException(status_code=502, detail="Linear token exchange failed") from exc
    config = {"access_token": encrypt(data["access_token"])}
    await _save_integration(org_id, "linear", config)
    return RedirectResponse(url=f"{get_settings().frontend_url}/dashboard/integrations", status_code=302)


@router.get("/jira/authorize")
async def jira_authorize(org_id: str, request: Request, org_id_from_token: str = Depends(_get_org_id)):
    if org_id_from_token != org_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    settings = get_settings()
    nonce = secrets.token_urlsafe(16)
    await _store_state(request, f"oauth:jira:{nonce}", org_id)
    redirect_uri = f"{settings.app_base_url}/api/v1/oauth/jira/callback"
    params = urllib.parse.urlencode(
        {
            "client_id": settings.jira_client_id,
            "response_type": "code",
            "audience": "api.atlassian.com",
            "scope": jira_oauth.SCOPES,
            "redirect_uri": redirect_uri,
            "state": nonce,
            "prompt": "consent",
        }
    )
    return RedirectResponse(f"{jira_oauth.AUTHORIZE_URL}?{params}", status_code=302)


@router.get("/jira/callback")
async def jira_callback(code: str, state: str, request: Request):
    settings = get_settings()
    org_id = await _pop_state(request, f"oauth:jira:{state}")
    if not org_id:
        raise HTTPException(status_code=400, detail="Invalid or expired OAuth state")
    redirect_uri = f"{settings.app_base_url}/api/v1/oauth/jira/callback"
    try:
        data = await _exchange_jira_code(code, redirect_uri)
    except Exception as exc:
        raise HTTPException(status_code=502, detail="Jira token exchange failed") from exc
    config = {
        "access_token": encrypt(data["access_token"]),
        "cloud_id": data.get("cloud_id", ""),
        "site_url": data.get("site_url", ""),
        "base_url": data.get("base_url", ""),
    }
    await _save_integration(org_id, "jira", config)
    return RedirectResponse(url=f"{get_settings().frontend_url}/dashboard/integrations", status_code=302)
