from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import stripe
from integrations.billing.stripe_sync import (
    create_stripe_checkout_session,
    parse_stripe_event,
    sync_subscription_event,
)
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
                "metadata": {
                    "plan": plan,
                    "seat_count": str(seat_count),
                },
            }
        },
    }


def test_parse_stripe_event_delegates_to_stripe_webhook():
    settings = MagicMock(stripe_webhook_secret="whsec_test")
    event_dict = {"type": "customer.subscription.created", "data": {"object": {}}}
    mock_event = MagicMock()
    mock_event.to_dict.return_value = event_dict
    with patch("integrations.billing.stripe_sync.stripe.Webhook.construct_event", return_value=mock_event) as mock_construct:
        parsed = parse_stripe_event(b'{"type":"x"}', "t=1,v1=abc", settings)

    assert parsed == event_dict
    mock_construct.assert_called_once_with(b'{"type":"x"}', "t=1,v1=abc", "whsec_test")


def test_parse_stripe_event_maps_invalid_signature_to_value_error():
    settings = MagicMock(stripe_webhook_secret="whsec_test")
    with (
        patch(
            "integrations.billing.stripe_sync.stripe.Webhook.construct_event",
            side_effect=stripe.SignatureVerificationError("bad", "sig"),
        ),
        pytest.raises(ValueError, match="Invalid signature"),
    ):
        parse_stripe_event(b'{"type":"x"}', "bad", settings)


def test_parse_stripe_event_maps_invalid_payload_to_value_error():
    settings = MagicMock(stripe_webhook_secret="whsec_test")
    with (
        patch(
            "integrations.billing.stripe_sync.stripe.Webhook.construct_event",
            side_effect=ValueError("bad json"),
        ),
        pytest.raises(ValueError, match="Invalid payload"),
    ):
        parse_stripe_event(b"not-json", "t=1,v1=abc", settings)


@pytest.mark.asyncio
async def test_create_stripe_checkout_session_passes_subscription_payload():
    with patch("integrations.billing.stripe_sync.stripe.checkout.Session.create") as mock_create:
        mock_create.return_value = MagicMock(url="https://checkout.stripe.com/pay/cs_test")

        checkout = await create_stripe_checkout_session(
            "sk_test",
            "cus_123",
            "price_team",
            "team",
            5,
            "https://example.com/success",
            "https://example.com/cancel",
        )

    assert checkout.url == "https://checkout.stripe.com/pay/cs_test"
    assert mock_create.call_args.kwargs == {
        "customer": "cus_123",
        "mode": "subscription",
        "line_items": [{"price": "price_team", "quantity": 5}],
        "subscription_data": {"metadata": {"plan": "team", "seat_count": "5"}},
        "success_url": "https://example.com/success",
        "cancel_url": "https://example.com/cancel",
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
async def test_updated_event_with_null_seat_count_defaults_to_one():
    billing = OrgBilling(org_id="org-1", plan="pro", seat_count=3, stripe_customer_id="cus_123", stripe_subscription_id="sub_abc")
    session = _make_session(billing)
    event = _make_event("customer.subscription.updated", "cus_123", "sub_abc", "team", 10)
    event["data"]["object"]["metadata"]["seat_count"] = None

    await sync_subscription_event(session, event)

    assert billing.plan == "team"
    assert billing.seat_count == 1
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


@pytest.mark.asyncio
async def test_unsupported_plan_value_is_noop():
    billing = OrgBilling(org_id="org-1", plan="pro", seat_count=2, stripe_customer_id="cus_123")
    session = _make_session(billing)
    event = _make_event("customer.subscription.updated", "cus_123", "sub_abc", "hacker_plan", 99)
    await sync_subscription_event(session, event)
    assert billing.plan == "pro"
    assert billing.seat_count == 2
    session.commit.assert_not_called()
