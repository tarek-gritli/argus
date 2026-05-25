from __future__ import annotations

import httpx

from .schemas import ReviewSummary

_NOTION_API = "https://api.notion.com/v1"
_NOTION_VERSION = "2022-06-28"


def fetch_page(api_key: str, page_id: str) -> dict:
    resp = httpx.get(
        f"{_NOTION_API}/pages/{page_id}",
        headers={"Authorization": f"Bearer {api_key}", "Notion-Version": _NOTION_VERSION},
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()


_REQUIRED_PROPERTIES = {
    "PR URL": {"url": {}},
    "Findings": {"number": {"format": "number"}},
    "Critical": {"number": {"format": "number"}},
    "High": {"number": {"format": "number"}},
}


async def _ensure_schema(client: httpx.AsyncClient, token: str, database_id: str) -> None:
    headers = {"Authorization": f"Bearer {token}", "Notion-Version": _NOTION_VERSION}
    resp = await client.get(f"{_NOTION_API}/databases/{database_id}", headers=headers)
    resp.raise_for_status()
    existing = set(resp.json().get("properties", {}).keys())
    missing = {k: v for k, v in _REQUIRED_PROPERTIES.items() if k not in existing}
    if missing:
        patch = await client.patch(
            f"{_NOTION_API}/databases/{database_id}",
            headers=headers,
            json={"properties": missing},
        )
        patch.raise_for_status()


async def append_to_notion_db(api_key: str, database_id: str, summary: ReviewSummary) -> None:
    async with httpx.AsyncClient() as client:
        await _ensure_schema(client, api_key, database_id)
        resp = await client.post(
            f"{_NOTION_API}/pages",
            headers={"Authorization": f"Bearer {api_key}", "Notion-Version": _NOTION_VERSION},
            json={
                "parent": {"database_id": database_id},
                "properties": {
                    "Name": {"title": [{"text": {"content": f"{summary.repo} PR #{summary.pr_number}"}}]},
                    "PR URL": {"url": summary.pr_url},
                    "Findings": {"number": summary.finding_count},
                    "Critical": {"number": summary.critical_count},
                    "High": {"number": summary.high_count},
                },
            },
        )
        resp.raise_for_status()
