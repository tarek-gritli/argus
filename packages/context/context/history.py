from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from shared.db import fresh_session_context
from shared.schemas import FindingSchema
from sqlalchemy import select

logger = logging.getLogger(__name__)


async def get_rejected_finding_keys(org_id: str, repo_id: str, lookback_days: int = 30) -> set[tuple[str, str]]:
    """Return (file, title) pairs for findings explicitly rejected in the last N days."""
    try:
        from shared.models import Finding, Review

        cutoff = datetime.now(timezone.utc) - timedelta(days=lookback_days)
        async with fresh_session_context() as session:
            result = await session.execute(
                select(Finding.file, Finding.title)
                .join(Review, Finding.review_id == Review.id)
                .where(
                    Review.repo_id == repo_id,
                    Review.org_id == org_id,
                    Finding.is_accepted == False,  # noqa: E712
                    Finding.created_at >= cutoff,
                )
            )
            return {(row.file, row.title) for row in result.all()}
    except Exception:
        logger.warning("get_rejected_finding_keys failed — suppression skipped", exc_info=True)
        return set()


def suppress_duplicate_findings(findings: list[FindingSchema], rejected: set[tuple[str, str]]) -> list[FindingSchema]:
    """Remove findings that match a (file, title) pair the user previously rejected."""
    if not rejected:
        return findings
    return [f for f in findings if (f.file, f.title) not in rejected]
