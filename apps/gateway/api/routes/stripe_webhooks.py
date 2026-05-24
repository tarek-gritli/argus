from __future__ import annotations

import logging

import stripe
from fastapi import APIRouter, Request, Response
from integrations.billing.stripe_sync import sync_subscription_event
from shared.config import get_settings
from shared.db import session_context

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/stripe")
async def stripe_webhook(request: Request) -> Response:
    payload = await request.body()
    sig = request.headers.get("stripe-signature")
    if not sig:
        return Response(status_code=400, content="Missing Stripe-Signature")

    settings = get_settings()
    if not settings.stripe_webhook_secret:
        logger.error("STRIPE_WEBHOOK_SECRET not configured")
        return Response(status_code=500, content="Stripe not configured")

    try:
        event = stripe.Webhook.construct_event(payload, sig, settings.stripe_webhook_secret)
    except stripe.error.SignatureVerificationError:
        return Response(status_code=400, content="Invalid signature")

    async with session_context() as session:
        await sync_subscription_event(session, event)

    return Response(status_code=200, content='{"ok":true}', media_type="application/json")
