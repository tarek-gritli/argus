from __future__ import annotations

import logging

from integrations.notifications.notion import fetch_page

from .base import TicketData

logger = logging.getLogger(__name__)


class NotionTicketProvider:
    def __init__(self, api_key: str) -> None:
        self._api_key = api_key

    def fetch(self, ticket_id: str) -> TicketData | None:
        try:
            page = fetch_page(self._api_key, ticket_id)
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
