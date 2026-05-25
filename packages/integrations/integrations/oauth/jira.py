from __future__ import annotations

import httpx

_TOKEN_URL = "https://auth.atlassian.com/oauth/token"
_RESOURCES_URL = "https://api.atlassian.com/oauth/token/accessible-resources"
AUTHORIZE_URL = "https://auth.atlassian.com/authorize"
SCOPES = "read:jira-work offline_access"


async def exchange_code(code: str, client_id: str, client_secret: str, redirect_uri: str) -> dict:
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            _TOKEN_URL,
            json={
                "grant_type": "authorization_code",
                "client_id": client_id,
                "client_secret": client_secret,
                "code": code,
                "redirect_uri": redirect_uri,
            },
        )
        resp.raise_for_status()
        return resp.json()


async def get_accessible_resources(access_token: str) -> list[dict]:
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            _RESOURCES_URL,
            headers={"Authorization": f"Bearer {access_token}", "Accept": "application/json"},
        )
        resp.raise_for_status()
        return resp.json()
