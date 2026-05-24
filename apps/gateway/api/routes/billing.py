from __future__ import annotations

import logging
from typing import Literal

import stripe
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field
from shared.config import get_settings
from shared.db import session_context
from shared.models.org_billing import OrgBilling
from sqlalchemy import select

router = APIRouter()
logger = logging.getLogger(__name__)


class CheckoutRequest(BaseModel):
    plan: Literal["pro", "team"]
    seats: int = Field(ge=1, le=500)


@router.post("/checkout")
async def create_checkout_session(body: CheckoutRequest, request: Request):
    org_id: str = request.state.org_id
    settings = get_settings()

    price_id = settings.stripe_pro_price_id if body.plan == "pro" else settings.stripe_team_price_id
    if not price_id or not settings.stripe_secret_key:
        raise HTTPException(status_code=503, detail="Stripe not configured")

    stripe.api_key = settings.stripe_secret_key

    async with session_context() as session:
        result = await session.execute(select(OrgBilling).where(OrgBilling.org_id == org_id))
        billing = result.scalar_one_or_none()
        if billing is None:
            raise HTTPException(status_code=404, detail="Billing record not found")

        customer_id = billing.stripe_customer_id
        if not customer_id:
            customer = stripe.Customer.create(metadata={"org_id": org_id})
            customer_id = customer.id
            billing.stripe_customer_id = customer_id
            await session.commit()

    checkout = stripe.checkout.Session.create(
        customer=customer_id,
        mode="subscription",
        line_items=[{"price": price_id, "quantity": body.seats}],
        subscription_data={"metadata": {"plan": body.plan, "seat_count": str(body.seats)}},
        success_url=settings.stripe_success_url,
        cancel_url=settings.stripe_cancel_url,
    )
    return {"checkout_url": checkout.url}


@router.post("/portal")
async def create_portal_session(request: Request):
    org_id: str = request.state.org_id
    settings = get_settings()

    if not settings.stripe_secret_key:
        raise HTTPException(status_code=503, detail="Stripe not configured")

    stripe.api_key = settings.stripe_secret_key

    async with session_context() as session:
        result = await session.execute(select(OrgBilling).where(OrgBilling.org_id == org_id))
        billing = result.scalar_one_or_none()
        if not billing or not billing.stripe_customer_id:
            raise HTTPException(status_code=400, detail="No active Stripe subscription")

    portal = stripe.billing_portal.Session.create(
        customer=billing.stripe_customer_id,
        return_url=settings.stripe_cancel_url,
    )
    return {"portal_url": portal.url}
