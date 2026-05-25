from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient


def _make_app():
    from api.routes.stripe_webhooks import router
    from fastapi import FastAPI

    app = FastAPI()
    app.include_router(router, prefix="/webhooks")
    return app


def _make_raw_event(event_type: str = "customer.subscription.created") -> bytes:
    return json.dumps(
        {
            "type": event_type,
            "data": {
                "object": {
                    "customer": "cus_1",
                    "id": "sub_1",
                    "items": {
                        "data": [
                            {
                                "price": {
                                    "metadata": {
                                        "plan": "pro",
                                        "seat_count": "2",
                                    }
                                }
                            }
                        ]
                    },
                }
            },
        }
    ).encode()


def _mock_settings():
    from shared.config import Settings

    s = MagicMock(spec=Settings)
    s.stripe_webhook_secret = "whsec_test"
    s.stripe_secret_key = "sk_test"
    return s


def test_stripe_webhook_valid_signature_returns_200():
    settings = _mock_settings()
    with (
        patch("api.routes.stripe_webhooks.get_settings", return_value=settings),
        patch("api.routes.stripe_webhooks.parse_stripe_event") as mock_parse,
        patch("api.routes.stripe_webhooks.session_context") as mock_gs,
        patch(
            "api.routes.stripe_webhooks.sync_subscription_event",
            new_callable=AsyncMock,
        ) as mock_sync,
    ):
        mock_parse.return_value = {"type": "customer.subscription.created", "data": {"object": {}}}
        mock_session = AsyncMock()
        mock_gs.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_gs.return_value.__aexit__ = AsyncMock(return_value=False)

        client = TestClient(_make_app(), raise_server_exceptions=False)
        resp = client.post(
            "/webhooks/stripe",
            content=_make_raw_event(),
            headers={"stripe-signature": "t=1,v1=abc"},
        )
    assert resp.status_code == 200
    mock_parse.assert_called_once_with(_make_raw_event(), "t=1,v1=abc", settings)
    mock_sync.assert_awaited_once_with(mock_session, mock_parse.return_value)


def test_stripe_webhook_invalid_signature_returns_400():
    with (
        patch("api.routes.stripe_webhooks.get_settings", return_value=_mock_settings()),
        patch(
            "api.routes.stripe_webhooks.parse_stripe_event",
            side_effect=ValueError("Invalid signature"),
        ),
    ):
        client = TestClient(_make_app(), raise_server_exceptions=False)
        resp = client.post(
            "/webhooks/stripe",
            content=b'{"type":"x"}',
            headers={"stripe-signature": "bad"},
        )
    assert resp.status_code == 400


def test_stripe_webhook_invalid_payload_returns_400():
    with (
        patch("api.routes.stripe_webhooks.get_settings", return_value=_mock_settings()),
        patch(
            "api.routes.stripe_webhooks.parse_stripe_event",
            side_effect=ValueError("Invalid payload"),
        ),
    ):
        client = TestClient(_make_app(), raise_server_exceptions=False)
        resp = client.post(
            "/webhooks/stripe",
            content=b"not-json",
            headers={"stripe-signature": "t=1,v1=abc"},
        )

    assert resp.status_code == 400
    assert resp.text == "Invalid payload"


def test_stripe_webhook_missing_signature_returns_400():
    client = TestClient(_make_app(), raise_server_exceptions=False)
    resp = client.post("/webhooks/stripe", content=b"{}")
    assert resp.status_code == 400
