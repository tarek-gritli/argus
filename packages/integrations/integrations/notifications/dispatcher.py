from __future__ import annotations

import asyncio
import logging

from shared.crypto import decrypt
from shared.models.org_integration import OrgIntegration
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .notion import append_to_notion_db
from .schemas import ReviewSummary
from .slack import post_to_slack

_SENSITIVE_KEYS = {"api_key", "webhook_url", "token"}


def _decrypt_config(config: dict) -> dict:
    result = {}
    for k, v in config.items():
        if k in _SENSITIVE_KEYS and isinstance(v, str) and v:
            try:
                result[k] = decrypt(v)
            except Exception:
                result[k] = v
        else:
            result[k] = v
    return result


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
            config = _decrypt_config(integration.config)
            if integration.kind == "slack":
                webhook_url = config.get("webhook_url", "")
                if webhook_url:
                    await asyncio.to_thread(post_to_slack, webhook_url, summary)
            elif integration.kind == "notion":
                token = config.get("token", "")
                database_id = config.get("database_id", "")
                if token and database_id:
                    await append_to_notion_db(token, database_id, summary)
        except Exception:
            logger.exception("Notification failed for integration %s (%s)", integration.id, integration.kind)
