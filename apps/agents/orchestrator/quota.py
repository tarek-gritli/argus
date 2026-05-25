from __future__ import annotations

from datetime import datetime, timezone

from shared.models import OrgBilling
from shared.models.org_billing import _next_month_start
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession


async def get_or_create_billing(session: AsyncSession, org_id: str) -> OrgBilling:
    result = await session.execute(select(OrgBilling).where(OrgBilling.org_id == org_id).with_for_update())
    billing = result.scalar_one_or_none()
    if billing is None:
        try:
            billing = OrgBilling(org_id=org_id)
            session.add(billing)
            await session.flush()
        except IntegrityError:
            await session.rollback()
            result = await session.execute(select(OrgBilling).where(OrgBilling.org_id == org_id).with_for_update())
            billing = result.scalar_one()
    return billing


async def check_and_increment_quota(session: AsyncSession, billing: OrgBilling) -> tuple[bool, str]:
    """Return (allowed, plan). Resets monthly count if needed."""
    now = datetime.now(timezone.utc)
    if now >= billing.quota_reset_at:
        billing.reviews_used_this_month = 0
        billing.quota_reset_at = _next_month_start()
        await session.commit()

    if billing.reviews_used_this_month >= billing.monthly_limit:
        return False, billing.plan

    billing.reviews_used_this_month += 1
    await session.commit()
    return True, billing.plan
