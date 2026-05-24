# apps/agents/specialized/ticket_compliance/providers/github_issues.py
from __future__ import annotations

import logging

from .base import TicketData

logger = logging.getLogger(__name__)


class GitHubIssuesProvider:
    def __init__(self, gh_client, repo_full_name: str) -> None:
        self._gh = gh_client
        self._repo_full_name = repo_full_name

    def fetch(self, ticket_id: str) -> TicketData | None:
        try:
            repo = self._gh.get_repo(self._repo_full_name)
            issue = repo.get_issue(int(ticket_id))
            return TicketData(
                id=ticket_id,
                title=issue.title,
                description=issue.body or "",
                url=issue.html_url,
            )
        except Exception:
            logger.debug("GitHubIssues: could not fetch #%s", ticket_id, exc_info=True)
            return None
