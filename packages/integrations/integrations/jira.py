from __future__ import annotations

import httpx


def fetch_issue(base_url: str, access_token: str, ticket_id: str) -> dict | None:
    url = f"{base_url.rstrip('/')}/rest/api/3/issue/{ticket_id}"
    resp = httpx.get(
        url,
        headers={"Authorization": f"Bearer {access_token}", "Accept": "application/json"},
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()
