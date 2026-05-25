from __future__ import annotations

import logging

from integrations.jira import fetch_issue

from .base import TicketData

logger = logging.getLogger(__name__)


class JiraProvider:
    def __init__(self, base_url: str, email: str, api_token: str) -> None:
        self._base_url = base_url
        self._email = email
        self._api_token = api_token

    def fetch(self, ticket_id: str) -> TicketData | None:
        try:
            data = fetch_issue(self._base_url, self._email, self._api_token, ticket_id)
            if not data:
                return None
            fields = data.get("fields", {})
            description_raw = fields.get("description") or ""
            description = description_raw if isinstance(description_raw, str) else str(description_raw)
            return TicketData(
                id=ticket_id,
                title=fields.get("summary", ""),
                description=description,
                url=f"{self._base_url.rstrip('/')}/browse/{ticket_id}",
            )
        except Exception:
            logger.debug("Jira: could not fetch %s", ticket_id, exc_info=True)
            return None
