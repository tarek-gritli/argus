from __future__ import annotations

import logging

import httpx

from .base import TicketData

logger = logging.getLogger(__name__)

_NOTION_API = "https://api.notion.com/v1"
_NOTION_VERSION = "2022-06-28"


class NotionTicketProvider:
    def __init__(self, api_key: str) -> None:
        self._headers = {
            "Authorization": f"Bearer {api_key}",
            "Notion-Version": _NOTION_VERSION,
        }

    def fetch(self, ticket_id: str) -> TicketData | None:
        try:
            resp = httpx.get(f"{_NOTION_API}/pages/{ticket_id}", headers=self._headers)
            resp.raise_for_status()
            page = resp.json()
            props = page.get("properties", {})
            title_prop = next(
                (p for p in props.values() if isinstance(p, dict) and p.get("type") == "title"),
                {},
            )
            title_parts = title_prop.get("title", [])
            title = "".join(part.get("plain_text", "") for part in title_parts)
            return TicketData(
                id=ticket_id,
                title=title,
                description="",
                url=page.get("url", ""),
            )
        except Exception:
            logger.debug("Notion: could not fetch page %s", ticket_id, exc_info=True)
            return None
