from __future__ import annotations

import logging

import httpx

from .base import TicketData

logger = logging.getLogger(__name__)


class JiraProvider:
    def __init__(self, base_url: str, email: str, api_token: str) -> None:
        self._base_url = base_url.rstrip("/")
        self._auth = (email, api_token)

    def fetch(self, ticket_id: str) -> TicketData | None:
        url = f"{self._base_url}/rest/api/3/issue/{ticket_id}"
        try:
            resp = httpx.get(url, auth=self._auth, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            fields = data.get("fields", {})
            description_raw = fields.get("description") or ""
            description = description_raw if isinstance(description_raw, str) else str(description_raw)
            return TicketData(
                id=ticket_id,
                title=fields.get("summary", ""),
                description=description,
                url=f"{self._base_url}/browse/{ticket_id}",
            )
        except Exception:
            logger.debug("Jira: could not fetch %s", ticket_id, exc_info=True)
            return None
