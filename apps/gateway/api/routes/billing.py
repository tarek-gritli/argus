from __future__ import annotations

import logging
from typing import Literal, NoReturn

from fastapi import APIRouter, HTTPException, Request
from integrations.billing.stripe_sync import (
    StripeBillingError,
    create_stripe_checkout_session,
    create_stripe_customer,
    create_stripe_portal_session,
)
from pydantic import BaseModel, Field
from shared.config import get_settings
from shared.db import session_context
from shared.models.org_billing import OrgBilling
from sqlalchemy import select

router = APIRouter()
logger = logging.getLogger(__name__)


def _raise_stripe_http_error(exc: StripeBillingError) -> NoReturn:
    logger.warning("Stripe billing request failed: %s", exc)
    raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc


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

    async with session_context() as session:
        result = await session.execute(select(OrgBilling).where(OrgBilling.org_id == org_id))
        billing = result.scalar_one_or_none()
        if billing is None:
            raise HTTPException(status_code=404, detail="Billing record not found")

        customer_id = billing.stripe_customer_id
        if not customer_id:
            try:
                customer = await create_stripe_customer(settings.stripe_secret_key, org_id)
            except StripeBillingError as exc:
                _raise_stripe_http_error(exc)
            customer_id = customer.id
            billing.stripe_customer_id = customer_id
            await session.commit()

    try:
        checkout = await create_stripe_checkout_session(
            settings.stripe_secret_key,
            customer_id,
            price_id,
            body.plan,
            body.seats,
            settings.stripe_success_url,
            settings.stripe_cancel_url,
        )
    except StripeBillingError as exc:
        _raise_stripe_http_error(exc)
    return {"checkout_url": checkout.url}


@router.post("/portal")
async def create_portal_session(request: Request):
    org_id: str = request.state.org_id
    settings = get_settings()

    if not settings.stripe_secret_key:
        raise HTTPException(status_code=503, detail="Stripe not configured")

    async with session_context() as session:
        result = await session.execute(select(OrgBilling).where(OrgBilling.org_id == org_id))
        billing = result.scalar_one_or_none()
        if not billing or not billing.stripe_customer_id:
            raise HTTPException(status_code=400, detail="No active Stripe subscription")

    try:
        portal = await create_stripe_portal_session(
            settings.stripe_secret_key,
            billing.stripe_customer_id,
            settings.stripe_cancel_url,
        )
    except StripeBillingError as exc:
        _raise_stripe_http_error(exc)
    return {"portal_url": portal.url}
