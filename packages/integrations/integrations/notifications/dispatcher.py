from __future__ import annotations

import asyncio
import logging

from shared.models.org_integration import OrgIntegration
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .notion import append_to_notion_db
from .schemas import ReviewSummary
from .slack import post_to_slack

logger = logging.getLogger(__name__)


async def dispatch_review_completed(session: AsyncSession, summary: ReviewSummary) -> None:
    result = await session.execute(
        select(OrgIntegration).where(
            OrgIntegration.org_id == summary.org_id,
            OrgIntegration.enabled.is_(True),
        )
    )
    integrations = result.scalars().all()

    for integration in integrations:
        try:
            if integration.kind == "slack":
                webhook_url = integration.config.get("webhook_url", "")
                if webhook_url:
                    await asyncio.to_thread(post_to_slack, webhook_url, summary)
            elif integration.kind == "notion":
                api_key = integration.config.get("api_key", "")
                database_id = integration.config.get("database_id", "")
                if api_key and database_id:
                    await append_to_notion_db(api_key, database_id, summary)
        except Exception:
            logger.exception("Notification failed for integration %s (%s)", integration.id, integration.kind)
