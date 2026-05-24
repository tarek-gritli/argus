from __future__ import annotations

import logging
from typing import Any

from shared.models.org_billing import OrgBilling
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

_HANDLED_EVENTS = frozenset(
    [
        "customer.subscription.created",
        "customer.subscription.updated",
        "customer.subscription.deleted",
    ]
)


async def sync_subscription_event(session: AsyncSession, event: Any) -> None:
    event_type = event.get("type", "")
    if event_type not in _HANDLED_EVENTS:
        return

    obj = event["data"]["object"]
    customer_id: str = obj["customer"]
    sub_id: str = obj["id"]

    result = await session.execute(select(OrgBilling).where(OrgBilling.stripe_customer_id == customer_id))
    billing = result.scalar_one_or_none()
    if billing is None:
        logger.warning("No OrgBilling found for stripe_customer_id=%s — skipping", customer_id)
        return

    if event_type == "customer.subscription.deleted":
        billing.plan = "free"
        billing.seat_count = 1
        billing.stripe_subscription_id = None
    else:
        items = obj.get("items", {}).get("data", [])
        if not items:
            logger.warning("Subscription %s has no items — skipping", sub_id)
            return
        metadata = items[0]["price"].get("metadata", {})
        plan = metadata.get("plan", "free")
        try:
            seat_count = int(metadata.get("seat_count", "1"))
        except ValueError:
            seat_count = 1

        billing.plan = plan
        billing.seat_count = max(1, seat_count)
        billing.stripe_customer_id = customer_id
        billing.stripe_subscription_id = sub_id

    await session.commit()
