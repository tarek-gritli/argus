from __future__ import annotations

import httpx

_TOKEN_URL = "https://slack.com/api/oauth.v2.access"
AUTHORIZE_URL = "https://slack.com/oauth/v2/authorize"
SCOPES = "incoming-webhook"


async def exchange_code(code: str, client_id: str, client_secret: str, redirect_uri: str) -> dict:
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            _TOKEN_URL,
            data={
                "code": code,
                "client_id": client_id,
                "client_secret": client_secret,
                "redirect_uri": redirect_uri,
            },
        )
        resp.raise_for_status()
        data = resp.json()
        if not data.get("ok"):
            raise ValueError(f"Slack OAuth error: {data.get('error')}")
        return data
