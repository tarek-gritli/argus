from __future__ import annotations

from fastapi import APIRouter, Request, Response
from integrations.billing.stripe_sync import parse_stripe_event, sync_subscription_event
from shared.config import get_settings
from shared.db import session_context

router = APIRouter()


@router.post("/stripe")
async def stripe_webhook(request: Request) -> Response:
    payload = await request.body()
    sig = request.headers.get("stripe-signature")
    if not sig:
        return Response(status_code=400, content="Missing Stripe-Signature")

    settings = get_settings()
    if not settings.stripe_webhook_secret:
        return Response(status_code=500, content="Stripe not configured")

    try:
        event = parse_stripe_event(payload, sig, settings)
    except ValueError as exc:
        return Response(status_code=400, content=str(exc))

    async with session_context() as session:
        await sync_subscription_event(session, event)

    return Response(status_code=200, content='{"ok":true}', media_type="application/json")
