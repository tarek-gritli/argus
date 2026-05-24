from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from integrations.billing.stripe_sync import sync_subscription_event
from shared.models.org_billing import OrgBilling


def _make_session(billing: OrgBilling | None):
    session = AsyncMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = billing
    session.execute = AsyncMock(return_value=result)
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    return session


def _make_event(event_type: str, customer_id: str, sub_id: str, plan: str, seat_count: int, status: str = "active"):
    return {
        "type": event_type,
        "data": {
            "object": {
                "id": sub_id,
                "customer": customer_id,
                "status": status,
                "items": {
                    "data": [
                        {
                            "price": {
                                "metadata": {
                                    "plan": plan,
                                    "seat_count": str(seat_count),
                                }
                            }
                        }
                    ]
                },
            }
        },
    }


@pytest.mark.asyncio
async def test_created_event_updates_existing_billing():
    billing = OrgBilling(org_id="org-1")
    session = _make_session(billing)
    event = _make_event("customer.subscription.created", "cus_123", "sub_abc", "pro", 3)
    await sync_subscription_event(session, event)
    assert billing.plan == "pro"
    assert billing.seat_count == 3
    assert billing.stripe_customer_id == "cus_123"
    assert billing.stripe_subscription_id == "sub_abc"
    session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_updated_event_changes_plan_and_seats():
    billing = OrgBilling(org_id="org-1", plan="pro", seat_count=3, stripe_customer_id="cus_123", stripe_subscription_id="sub_abc")
    session = _make_session(billing)
    event = _make_event("customer.subscription.updated", "cus_123", "sub_abc", "team", 10)
    await sync_subscription_event(session, event)
    assert billing.plan == "team"
    assert billing.seat_count == 10
    session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_deleted_event_resets_to_free():
    billing = OrgBilling(org_id="org-1", plan="pro", seat_count=5, stripe_customer_id="cus_123", stripe_subscription_id="sub_abc")
    session = _make_session(billing)
    event = _make_event("customer.subscription.deleted", "cus_123", "sub_abc", "pro", 5)
    await sync_subscription_event(session, event)
    assert billing.plan == "free"
    assert billing.seat_count == 1
    session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_no_billing_row_for_customer_is_noop():
    session = _make_session(None)
    event = _make_event("customer.subscription.updated", "cus_unknown", "sub_abc", "pro", 1)
    await sync_subscription_event(session, event)
    session.commit.assert_not_called()


@pytest.mark.asyncio
async def test_unknown_event_type_is_noop():
    billing = OrgBilling(org_id="org-1")
    session = _make_session(billing)
    event = {"type": "invoice.payment_succeeded", "data": {"object": {}}}
    await sync_subscription_event(session, event)
    session.commit.assert_not_called()
