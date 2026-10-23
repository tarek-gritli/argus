from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.mark.asyncio
async def test_send_email_posts_to_resend():
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.post = AsyncMock(return_value=mock_response)

    with patch("httpx.AsyncClient", return_value=mock_client):
        from integrations.email.client import send_email

        await send_email("re_test_key", "user@example.com", "Hello", "<p>Hello</p>")

    mock_client.post.assert_called_once()
    call_kwargs = mock_client.post.call_args
    assert call_kwargs.args[0] == "https://api.resend.com/emails"
    assert call_kwargs.kwargs["headers"]["Authorization"] == "Bearer re_test_key"
    assert call_kwargs.kwargs["json"]["to"] == ["user@example.com"]


def test_invoice_receipt_html_contains_amount_and_number():
    from integrations.email.client import invoice_receipt_html

    html = invoice_receipt_html("pro", 2900, "INV-0001", "https://stripe.com/invoice.pdf")
    assert "$29.00" in html
    assert "INV-0001" in html
    assert "https://stripe.com/invoice.pdf" in html
    assert "Pro" in html


def test_invite_html_contains_org_and_link():
    from integrations.email.client import invite_html

    html = invite_html("Acme Corp", "jdoe", "https://app.argus.ai/invite/abc123")
    assert "Acme Corp" in html
    assert "jdoe" in html
    assert "https://app.argus.ai/invite/abc123" in html
