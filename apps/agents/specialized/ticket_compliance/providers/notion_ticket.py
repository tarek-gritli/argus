from __future__ import annotations

import logging

from notion_client import Client

from .base import TicketData

logger = logging.getLogger(__name__)


class NotionTicketProvider:
    def __init__(self, api_key: str) -> None:
        self._client = Client(auth=api_key)

    def fetch(self, ticket_id: str) -> TicketData | None:
        try:
            page = self._client.pages.retrieve(page_id=ticket_id)
            props = page.get("properties", {})  # type: ignore[union-attr]
            title_prop = props.get("title") or props.get("Name") or {}
            title_parts = title_prop.get("title", [])
            title = "".join(part.get("plain_text", "") for part in title_parts)
            url = page.get("url", "")  # type: ignore[union-attr]
            return TicketData(
                id=ticket_id,
                title=title,
                description="",
                url=url,
            )
        except Exception:
            logger.debug("Notion: could not fetch page %s", ticket_id, exc_info=True)
            return None
