from __future__ import annotations

from datetime import datetime, timezone

from shared.models import OrgBilling
from shared.models.org_billing import _next_month_start
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


async def get_org_billing(session: AsyncSession, org_id: str) -> OrgBilling | None:
    result = await session.execute(select(OrgBilling).where(OrgBilling.org_id == org_id))
    return result.scalar_one_or_none()


async def check_and_increment_quota(session: AsyncSession, billing: OrgBilling) -> bool:
    """Return True if review is allowed, False if quota exceeded. Resets monthly count if needed."""
    now = datetime.now(timezone.utc)
    if now >= billing.quota_reset_at:
        billing.reviews_used_this_month = 0
        billing.quota_reset_at = _next_month_start()
        await session.flush()

    if billing.reviews_used_this_month >= billing.monthly_limit:
        return False

    billing.reviews_used_this_month += 1
    await session.commit()
    return True
