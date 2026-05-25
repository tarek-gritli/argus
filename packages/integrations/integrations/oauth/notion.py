from __future__ import annotations

import httpx

_TOKEN_URL = "https://api.notion.com/v1/oauth/token"
AUTHORIZE_URL = "https://api.notion.com/v1/oauth/authorize"


async def exchange_code(code: str, client_id: str, client_secret: str, redirect_uri: str) -> dict:
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            _TOKEN_URL,
            auth=(client_id, client_secret),
            json={"grant_type": "authorization_code", "code": code, "redirect_uri": redirect_uri},
        )
        resp.raise_for_status()
        return resp.json()
