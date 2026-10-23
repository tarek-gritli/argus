from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_list_stripe_invoices_maps_fields():
    fake_invoices = {
        "data": [
            {
                "id": "in_abc",
                "number": "INV-0001",
                "amount_paid": 2900,
                "created": 1700000000,
                "invoice_pdf": "https://stripe.com/pdf",
                "status": "paid",
            }
        ]
    }
    with patch(
        "integrations.billing.stripe_sync._run_stripe_call",
        new=AsyncMock(return_value=fake_invoices),
    ):
        from integrations.billing.stripe_sync import list_stripe_invoices

        result = await list_stripe_invoices("sk_test", "cus_abc")

    assert len(result) == 1
    assert result[0]["id"] == "in_abc"
    assert result[0]["amount_paid"] == 2900
    assert result[0]["invoice_pdf"] == "https://stripe.com/pdf"


def _session_with(billing):
    session = AsyncMock(spec=AsyncSession)
    session.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=billing)))
    return session


@pytest.mark.asyncio
async def test_sync_invoice_paid_sends_email():
    billing = MagicMock()
    billing.billing_email = "owner@example.com"
    billing.plan = "pro"

    event = {
        "type": "invoice.paid",
        "data": {
            "object": {
                "customer": "cus_abc",
                "amount_paid": 2900,
                "number": "INV-0001",
                "invoice_pdf": "https://stripe.com/pdf",
            }
        },
    }

    with (
        patch("integrations.billing.stripe_sync.send_email", new=AsyncMock()) as mock_send,
        patch("integrations.billing.stripe_sync._resend_key", return_value="re_test"),
    ):
        from integrations.billing.stripe_sync import sync_subscription_event

        await sync_subscription_event(_session_with(billing), event)

    mock_send.assert_called_once()
    assert mock_send.call_args.args[1] == "owner@example.com"


@pytest.mark.asyncio
async def test_sync_checkout_completed_stores_billing_email():
    billing = MagicMock()
    session = _session_with(billing)
    event = {
        "type": "checkout.session.completed",
        "data": {"object": {"customer": "cus_abc", "customer_details": {"email": "o@example.com"}}},
    }
    from integrations.billing.stripe_sync import sync_subscription_event

    await sync_subscription_event(session, event)

    assert billing.billing_email == "o@example.com"
    session.commit.assert_awaited_once()
