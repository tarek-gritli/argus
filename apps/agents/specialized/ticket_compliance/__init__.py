from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from shared.crypto import decrypt
from shared.models.org_integration import OrgIntegration
from shared.schemas import FindingSchema
from sqlalchemy import select

from .agent import run_ticket_compliance_agent
from .providers.github_issues import GitHubIssuesProvider
from .providers.jira import JiraProvider
from .providers.linear import LinearProvider
from .schemas import AgentInput

if TYPE_CHECKING:
    from integrations.github.schemas import PullRequestPayload

logger = logging.getLogger(__name__)

__all__ = ["analyze"]


async def _load_ticket_integrations(org_id: str) -> dict:
    from shared.db import session_context

    providers: dict = {}
    async with session_context() as session:
        result = await session.execute(
            select(OrgIntegration).where(
                OrgIntegration.org_id == org_id,
                OrgIntegration.kind.in_(["linear", "jira"]),
                OrgIntegration.enabled.is_(True),
            )
        )
        for integration in result.scalars().all():
            config = integration.config
            if integration.kind == "linear":
                token = config.get("access_token", "")
                if token:
                    try:
                        providers["linear"] = LinearProvider(access_token=decrypt(token))
                    except Exception:
                        logger.debug("ticket_compliance: failed to load Linear provider", exc_info=True)
            elif integration.kind == "jira":
                token = config.get("access_token", "")
                cloud_id = config.get("cloud_id", "")
                if token and cloud_id:
                    try:
                        providers["jira"] = JiraProvider(
                            access_token=decrypt(token),
                            cloud_id=cloud_id,
                            site_url=config.get("site_url", ""),
                        )
                    except Exception:
                        logger.debug("ticket_compliance: failed to load Jira provider", exc_info=True)
    return providers


def _build_providers(installation_id: int, repo_full_name: str, org_id: str) -> dict:
    providers: dict = {}
    if installation_id:
        try:
            from integrations.github.client import get_installation_client

            gh = get_installation_client(installation_id)
            providers["github_issues"] = GitHubIssuesProvider(gh_client=gh, repo_full_name=repo_full_name)
        except Exception:
            logger.debug("ticket_compliance: GitHub Issues provider unavailable", exc_info=True)
    if org_id:
        try:
            from workers.connections import run_async

            providers.update(run_async(_load_ticket_integrations(org_id)))
        except Exception:
            logger.debug("ticket_compliance: failed to load DB ticket integrations", exc_info=True)
    return providers


def analyze(files: list[Any], diff: str, pr_payload: "PullRequestPayload") -> list[FindingSchema]:
    agent_input = AgentInput(
        diff=diff,
        repo_full_name=pr_payload.repo_full_name,
        pr_number=pr_payload.pr_number,
        head_sha=pr_payload.head_sha,
        base_sha=pr_payload.base_sha,
        installation_id=pr_payload.installation_id,
        pr_title=getattr(pr_payload, "pr_title", None) or "",
        pr_description=getattr(pr_payload, "pr_body", None) or "",
    )
    org_id = getattr(pr_payload, "org_id", None) or ""
    providers = _build_providers(pr_payload.installation_id, pr_payload.repo_full_name, org_id)
    return run_ticket_compliance_agent(agent_input, providers)
