from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from typing import Any

import stripe
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


class StripeBillingError(Exception):
    def __init__(self, status_code: int, detail: str) -> None:
        self.status_code = status_code
        self.detail = detail
        super().__init__(detail)


async def _run_stripe_call(api_key: str, func: Callable[..., Any], **kwargs: Any) -> Any:
    def call() -> Any:
        stripe.api_key = api_key
        return func(**kwargs)

    try:
        return await asyncio.to_thread(call)
    except stripe.StripeError as exc:
        status_code = exc.http_status if exc.http_status and 400 <= exc.http_status < 500 else 502
        detail = exc.user_message or str(exc) or "Stripe request failed"
        raise StripeBillingError(status_code=status_code, detail=detail) from exc


def parse_stripe_event(raw_body: bytes, sig_header: str, settings: Any) -> Any:
    try:
        return stripe.Webhook.construct_event(raw_body, sig_header, settings.stripe_webhook_secret)
    except stripe.SignatureVerificationError as exc:
        raise ValueError("Invalid signature") from exc
    except ValueError as exc:
        raise ValueError("Invalid payload") from exc


async def create_stripe_customer(api_key: str, org_id: str) -> Any:
    return await _run_stripe_call(api_key, stripe.Customer.create, metadata={"org_id": org_id})


async def create_stripe_checkout_session(
    api_key: str,
    customer_id: str,
    price_id: str,
    plan: str,
    seats: int,
    success_url: str,
    cancel_url: str,
) -> Any:
    return await _run_stripe_call(
        api_key,
        stripe.checkout.Session.create,
        customer=customer_id,
        mode="subscription",
        line_items=[{"price": price_id, "quantity": seats}],
        subscription_data={"metadata": {"plan": plan, "seat_count": str(seats)}},
        success_url=success_url,
        cancel_url=cancel_url,
    )


async def create_stripe_portal_session(api_key: str, customer_id: str, return_url: str) -> Any:
    return await _run_stripe_call(
        api_key,
        stripe.billing_portal.Session.create,
        customer=customer_id,
        return_url=return_url,
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
        except (TypeError, ValueError):
            seat_count = 1

        billing.plan = plan
        billing.seat_count = max(1, seat_count)
        billing.stripe_customer_id = customer_id
        billing.stripe_subscription_id = sub_id

    await session.commit()
