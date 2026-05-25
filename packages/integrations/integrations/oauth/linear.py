from __future__ import annotations

import httpx

_TOKEN_URL = "https://api.linear.app/oauth/token"
AUTHORIZE_URL = "https://linear.app/oauth/authorize"
SCOPES = "read"


async def exchange_code(code: str, client_id: str, client_secret: str, redirect_uri: str) -> dict:
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            _TOKEN_URL,
            data={
                "grant_type": "authorization_code",
                "code": code,
                "client_id": client_id,
                "client_secret": client_secret,
                "redirect_uri": redirect_uri,
            },
        )
        resp.raise_for_status()
        return resp.json()
