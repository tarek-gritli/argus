from __future__ import annotations

import logging

import httpx

from .base import TicketData

logger = logging.getLogger(__name__)

_GRAPHQL_URL = "https://api.linear.app/graphql"

_QUERY = """
query IssueByIdentifier($identifier: String!) {
  issue(id: $identifier) {
    identifier
    title
    description
    url
  }
}
"""


class LinearProvider:
    def __init__(self, api_key: str) -> None:
        self._api_key = api_key

    def fetch(self, ticket_id: str) -> TicketData | None:
        try:
            resp = httpx.post(
                _GRAPHQL_URL,
                headers={"Authorization": self._api_key, "Content-Type": "application/json"},
                json={"query": _QUERY, "variables": {"identifier": ticket_id}},
                timeout=10,
            )
            resp.raise_for_status()
            issue = resp.json().get("data", {}).get("issue")
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
