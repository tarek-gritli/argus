from __future__ import annotations

import httpx

from .schemas import ReviewSummary

_NOTION_API = "https://api.notion.com/v1"
_NOTION_VERSION = "2022-06-28"


async def append_to_notion_db(api_key: str, database_id: str, summary: ReviewSummary) -> None:
    async with httpx.AsyncClient() as client:
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
