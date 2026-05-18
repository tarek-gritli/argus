from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from shared.schemas import FindingSchema

from .agent import run_ticket_compliance_agent
from .providers.github_issues import GitHubIssuesProvider
from .schemas import AgentInput

if TYPE_CHECKING:
    from integrations.github.schemas import PullRequestPayload

logger = logging.getLogger(__name__)

__all__ = ["analyze"]


def _build_providers(installation_id: int, repo_full_name: str) -> dict:
    providers = {}
    if installation_id:
        try:
            from integrations.github.client import get_installation_client

            gh = get_installation_client(installation_id)
            providers["github_issues"] = GitHubIssuesProvider(gh_client=gh, repo_full_name=repo_full_name)
        except Exception:
            logger.debug("ticket_compliance: GitHub Issues provider unavailable", exc_info=True)
    return providers


def analyze(files: list[Any], diff: str, pr_payload: "PullRequestPayload") -> list[FindingSchema]:
    """Adapter: build AgentInput + providers, then run the ticket compliance agent."""
    agent_input = AgentInput(
        diff=diff,
        repo_full_name=pr_payload.repo_full_name,
        pr_number=pr_payload.pr_number,
        head_sha=pr_payload.head_sha,
        base_sha=pr_payload.base_sha,
        installation_id=pr_payload.installation_id,
        pr_title=getattr(pr_payload, "pr_title", ""),
        pr_description=getattr(pr_payload, "pr_body", ""),
    )
    providers = _build_providers(pr_payload.installation_id, pr_payload.repo_full_name)
    return run_ticket_compliance_agent(agent_input, providers)
