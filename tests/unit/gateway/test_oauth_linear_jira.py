import asyncio
from unittest.mock import AsyncMock, patch

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient


def _make_app(org_id: str = "org-1"):
    from api.routes.oauth import _get_org_id, router

    app = FastAPI()
    app.state.redis = AsyncMock()
    app.include_router(router, prefix="/api/v1/oauth")
    app.dependency_overrides[_get_org_id] = lambda: org_id
    return app


def test_linear_authorize_redirects():
    app = _make_app()
    with (
        patch("api.routes.oauth.get_settings") as mock_settings,
        patch("api.routes.oauth._store_state", new=AsyncMock()),
    ):
        mock_settings.return_value.linear_client_id = "LIN_ID"
        mock_settings.return_value.app_base_url = "https://app.example.com"

        async def run():
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                return await client.get("/api/v1/oauth/linear/authorize?org_id=org-1", follow_redirects=False)

        resp = asyncio.run(run())

    assert resp.status_code == 302
    assert "linear.app/oauth/authorize" in resp.headers["location"]


def test_linear_callback_saves_integration():
    app = _make_app()
    with (
        patch("api.routes.oauth.get_settings") as mock_settings,
        patch("api.routes.oauth._pop_state", new=AsyncMock(return_value="org-1")),
        patch("api.routes.oauth._exchange_linear_code", new=AsyncMock(return_value={"access_token": "lin_oauth_tok"})),
        patch("api.routes.oauth._save_integration", new=AsyncMock()),
        patch("api.routes.oauth.encrypt", side_effect=lambda v: f"enc:{v}"),
    ):
        mock_settings.return_value.app_base_url = "https://app.example.com"

        async def run():
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                return await client.get("/api/v1/oauth/linear/callback?code=abc&state=nonce")

        resp = asyncio.run(run())

    assert resp.status_code == 200
    assert resp.json() == {"status": "connected"}


def test_linear_callback_invalid_state_returns_400():
    app = _make_app()
    with (
        patch("api.routes.oauth.get_settings"),
        patch("api.routes.oauth._pop_state", new=AsyncMock(return_value=None)),
    ):

        async def run():
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                return await client.get("/api/v1/oauth/linear/callback?code=abc&state=bad")

        resp = asyncio.run(run())

    assert resp.status_code == 400


def test_jira_authorize_redirects():
    app = _make_app()
    with (
        patch("api.routes.oauth.get_settings") as mock_settings,
        patch("api.routes.oauth._store_state", new=AsyncMock()),
    ):
        mock_settings.return_value.jira_client_id = "JIRA_ID"
        mock_settings.return_value.app_base_url = "https://app.example.com"

        async def run():
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                return await client.get("/api/v1/oauth/jira/authorize?org_id=org-1", follow_redirects=False)

        resp = asyncio.run(run())

    assert resp.status_code == 302
    assert "auth.atlassian.com/authorize" in resp.headers["location"]


def test_jira_callback_saves_integration():
    app = _make_app()
    with (
        patch("api.routes.oauth.get_settings") as mock_settings,
        patch("api.routes.oauth._pop_state", new=AsyncMock(return_value="org-1")),
        patch(
            "api.routes.oauth._exchange_jira_code",
            new=AsyncMock(
                return_value={
                    "access_token": "jira_tok",
                    "cloud_id": "cloud-uuid-1",
                    "base_url": "https://api.atlassian.com/ex/jira/cloud-uuid-1",
                }
            ),
        ),
        patch("api.routes.oauth._save_integration", new=AsyncMock()),
        patch("api.routes.oauth.encrypt", side_effect=lambda v: f"enc:{v}"),
    ):
        mock_settings.return_value.app_base_url = "https://app.example.com"

        async def run():
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                return await client.get("/api/v1/oauth/jira/callback?code=abc&state=nonce")

        resp = asyncio.run(run())

    assert resp.status_code == 200
    assert resp.json() == {"status": "connected"}


def test_jira_callback_invalid_state_returns_400():
    app = _make_app()
    with (
        patch("api.routes.oauth.get_settings"),
        patch("api.routes.oauth._pop_state", new=AsyncMock(return_value=None)),
    ):

        async def run():
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                return await client.get("/api/v1/oauth/jira/callback?code=abc&state=bad")

        resp = asyncio.run(run())

    assert resp.status_code == 400
