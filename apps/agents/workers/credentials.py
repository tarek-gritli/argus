from __future__ import annotations

from shared.crypto import decrypt
from shared.models.org_integration import OrgIntegration
from sqlalchemy import select

from .connections import get_session_factory


async def load_gitlab_credentials(org_id: str, integration_id: str) -> tuple[str, str]:
    """Instance URL + access token for this org's GitLab integration (never taken from a task payload)."""
    async with get_session_factory()() as session:
        row = (
            await session.execute(
                select(OrgIntegration).where(
                    OrgIntegration.id == integration_id,
                    OrgIntegration.org_id == org_id,
                    OrgIntegration.kind == "gitlab",
                    OrgIntegration.enabled.is_(True),
                )
            )
        ).scalar_one_or_none()
    if row is None:
        raise ValueError(f"No enabled GitLab integration {integration_id} for org {org_id}")
    return row.config["base_url"], decrypt(row.config["access_token"])
