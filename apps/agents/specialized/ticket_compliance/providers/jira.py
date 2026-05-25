from __future__ import annotations

import logging

from integrations.jira import fetch_issue

from .base import TicketData

logger = logging.getLogger(__name__)


class JiraProvider:
    def __init__(self, access_token: str, cloud_id: str, site_url: str = "") -> None:
        self._access_token = access_token
        self._api_base = f"https://api.atlassian.com/ex/jira/{cloud_id}"
        self._site_url = site_url or self._api_base

    def fetch(self, ticket_id: str) -> TicketData | None:
        try:
            data = fetch_issue(self._api_base, self._access_token, ticket_id)
            if not data:
                return None
            fields = data.get("fields", {})
            description_raw = fields.get("description") or ""
            description = description_raw if isinstance(description_raw, str) else str(description_raw)
            return TicketData(
                id=ticket_id,
                title=fields.get("summary", ""),
                description=description,
                url=f"{self._site_url}/browse/{ticket_id}",
            )
        except Exception:
            logger.debug("Jira: could not fetch %s", ticket_id, exc_info=True)
            return None
