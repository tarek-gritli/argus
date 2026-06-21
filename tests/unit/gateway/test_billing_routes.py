from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from integrations.billing.stripe_sync import StripeBillingError


def _make_app():
    from api.routes.billing import router

    app = FastAPI()

    @app.middleware("http")
    async def inject_org(request: Request, call_next):
        request.state.org_id = "org-1"
        request.state.user_id = "user-1"
        return await call_next(request)

    app.include_router(router, prefix="/billing")
    return app


def _make_billing(stripe_customer_id: str | None = None):
    from shared.models.org_billing import OrgBilling

    b = OrgBilling(org_id="org-1", plan="free", seat_count=1)
    b.stripe_customer_id = stripe_customer_id
    return b


def _mock_settings():
    from shared.config import Settings

    s = MagicMock(spec=Settings)
    s.stripe_secret_key = "sk_test"
    s.stripe_pro_price_id = "price_pro"
    s.stripe_team_price_id = "price_team"
    s.stripe_success_url = "https://example.com/success"
    s.stripe_cancel_url = "https://example.com/cancel"
    return s


def _mock_session(billing):
    session = AsyncMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = billing
    session.execute = AsyncMock(return_value=result)
    session.commit = AsyncMock()
    ctx = MagicMock()
    ctx.__aenter__ = AsyncMock(return_value=session)
    ctx.__aexit__ = AsyncMock(return_value=False)
    return ctx


def test_checkout_returns_url_for_pro_plan():
    with (
        patch("api.routes.billing.get_settings", return_value=_mock_settings()),
        patch("api.routes.billing.session_context", return_value=_mock_session(_make_billing())),
        patch("api.routes.billing.create_stripe_customer", new_callable=AsyncMock) as mock_cc,
        patch("api.routes.billing.create_stripe_checkout_session", new_callable=AsyncMock) as mock_checkout,
    ):
        mock_cc.return_value = MagicMock(id="cus_new")
        mock_checkout.return_value = MagicMock(url="https://checkout.stripe.com/pay/cs_test_abc")

        client = TestClient(_make_app())
        resp = client.post("/billing/checkout", json={"plan": "pro", "seats": 2})

    assert resp.status_code == 200
    assert resp.json()["checkout_url"] == "https://checkout.stripe.com/pay/cs_test_abc"
    mock_cc.assert_awaited_once_with("sk_test", "org-1")
    mock_checkout.assert_awaited_once_with(
        "sk_test",
        "cus_new",
        "price_pro",
        "pro",
        2,
        "https://example.com/success",
        "https://example.com/cancel",
    )


def test_checkout_reuses_existing_stripe_customer():
    with (
        patch("api.routes.billing.get_settings", return_value=_mock_settings()),
        patch(
            "api.routes.billing.session_context",
            return_value=_mock_session(_make_billing(stripe_customer_id="cus_existing")),
        ),
        patch("api.routes.billing.create_stripe_customer", new_callable=AsyncMock) as mock_cc,
        patch("api.routes.billing.create_stripe_checkout_session", new_callable=AsyncMock) as mock_checkout,
    ):
        mock_checkout.return_value = MagicMock(url="https://checkout.stripe.com/pay/cs_test_xyz")

        client = TestClient(_make_app())
        resp = client.post("/billing/checkout", json={"plan": "team", "seats": 5})

    mock_cc.assert_not_awaited()
    assert resp.status_code == 200
    assert resp.json()["checkout_url"] == "https://checkout.stripe.com/pay/cs_test_xyz"
    mock_checkout.assert_awaited_once_with(
        "sk_test",
        "cus_existing",
        "price_team",
        "team",
        5,
        "https://example.com/success",
        "https://example.com/cancel",
    )


def test_checkout_invalid_plan_returns_422():
    client = TestClient(_make_app())
    resp = client.post("/billing/checkout", json={"plan": "enterprise", "seats": 1})
    assert resp.status_code == 422


def test_checkout_maps_stripe_customer_error_to_http_response():
    session_ctx = _mock_session(_make_billing())
    with (
        patch("api.routes.billing.get_settings", return_value=_mock_settings()),
        patch("api.routes.billing.session_context", return_value=session_ctx),
        patch(
            "api.routes.billing.create_stripe_customer",
            new_callable=AsyncMock,
            side_effect=StripeBillingError(502, "Stripe unavailable"),
        ),
        patch("api.routes.billing.create_stripe_checkout_session", new_callable=AsyncMock) as mock_checkout,
    ):
        client = TestClient(_make_app())
        resp = client.post("/billing/checkout", json={"plan": "pro", "seats": 2})

    assert resp.status_code == 502
    assert resp.json()["detail"] == "Stripe unavailable"
    session_ctx.__aenter__.return_value.commit.assert_not_awaited()
    mock_checkout.assert_not_awaited()


def test_checkout_maps_stripe_session_error_to_http_response():
    with (
        patch("api.routes.billing.get_settings", return_value=_mock_settings()),
        patch(
            "api.routes.billing.session_context",
            return_value=_mock_session(_make_billing(stripe_customer_id="cus_existing")),
        ),
        patch(
            "api.routes.billing.create_stripe_checkout_session",
            new_callable=AsyncMock,
            side_effect=StripeBillingError(502, "Stripe unavailable"),
        ),
    ):
        client = TestClient(_make_app())
        resp = client.post("/billing/checkout", json={"plan": "team", "seats": 5})

    assert resp.status_code == 502
    assert resp.json()["detail"] == "Stripe unavailable"


def test_portal_returns_url():
    with (
        patch("api.routes.billing.get_settings", return_value=_mock_settings()),
        patch("api.routes.billing.session_context", return_value=_mock_session(_make_billing(stripe_customer_id="cus_123"))),
        patch("api.routes.billing.create_stripe_portal_session", new_callable=AsyncMock) as mock_ps,
    ):
        mock_ps.return_value = MagicMock(url="https://billing.stripe.com/p/session_abc")

        client = TestClient(_make_app())
        resp = client.post("/billing/portal")

    assert resp.status_code == 200
    assert resp.json()["portal_url"] == "https://billing.stripe.com/p/session_abc"
    mock_ps.assert_awaited_once_with("sk_test", "cus_123", "https://example.com/cancel")


def test_portal_maps_stripe_error_to_http_response():
    with (
        patch("api.routes.billing.get_settings", return_value=_mock_settings()),
        patch(
            "api.routes.billing.session_context",
            return_value=_mock_session(_make_billing(stripe_customer_id="cus_123")),
        ),
        patch(
            "api.routes.billing.create_stripe_portal_session",
            new_callable=AsyncMock,
            side_effect=StripeBillingError(400, "Invalid customer"),
        ),
    ):
        client = TestClient(_make_app())
        resp = client.post("/billing/portal")

    assert resp.status_code == 400
    assert resp.json()["detail"] == "Invalid customer"


def test_portal_no_customer_returns_400():
    with (
        patch("api.routes.billing.get_settings", return_value=_mock_settings()),
        patch("api.routes.billing.session_context", return_value=_mock_session(_make_billing(stripe_customer_id=None))),
    ):
        client = TestClient(_make_app())
        resp = client.post("/billing/portal")

    assert resp.status_code == 400


def test_get_billing_returns_plan_and_quota():
    from shared.models.org_billing import OrgBilling

    b = OrgBilling(org_id="org-1", plan="pro", seat_count=3, reviews_used_this_month=42, stripe_customer_id="cus_test")

    with patch("api.routes.billing.session_context", return_value=_mock_session(b)):
        client = TestClient(_make_app())
        resp = client.get("/billing/")

    assert resp.status_code == 200
    data = resp.json()
    assert data["plan"] == "pro"
    assert data["seat_count"] == 3
    assert data["reviews_used_this_month"] == 42
    assert data["monthly_limit"] == 300
    assert data["has_stripe_customer"]


def test_get_billing_404_when_no_record():
    with patch("api.routes.billing.session_context", return_value=_mock_session(None)):
        client = TestClient(_make_app())
        resp = client.get("/billing/")

    assert resp.status_code == 404
