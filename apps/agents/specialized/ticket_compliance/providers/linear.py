from __future__ import annotations

import logging

from integrations.linear import fetch_issue

from .base import TicketData

logger = logging.getLogger(__name__)


class LinearProvider:
    def __init__(self, access_token: str) -> None:
        self._access_token = access_token

    def fetch(self, ticket_id: str) -> TicketData | None:
        try:
            issue = fetch_issue(self._access_token, ticket_id)
            if not issue:
                return None
            return TicketData(
                id=ticket_id,
                title=issue.get("title", ""),
                description=issue.get("description") or "",
                url=issue.get("url", ""),
            )
        except Exception:
            logger.debug("Linear: could not fetch %s", ticket_id, exc_info=True)
            return None
