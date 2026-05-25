import asyncio
from unittest.mock import AsyncMock, patch

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient


def _make_app():
    from api.routes.oauth import router

    app = FastAPI()
    app.state.redis = AsyncMock()
    app.include_router(router, prefix="/api/v1/oauth")
    return app


# ─── Slack ────────────────────────────────────────────────────────────────────


def test_slack_authorize_redirects():
    app = _make_app()

    with (
        patch("api.routes.oauth.get_settings") as mock_settings,
        patch("api.routes.oauth._store_state", new=AsyncMock()),
    ):
        mock_settings.return_value.slack_client_id = "CLIENT_ID"
        mock_settings.return_value.app_base_url = "https://app.example.com"

        async def run():
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                return await client.get("/api/v1/oauth/slack/authorize?org_id=org-1", follow_redirects=False)

        resp = asyncio.run(run())

    assert resp.status_code == 302
    assert "slack.com/oauth/v2/authorize" in resp.headers["location"]


def test_slack_callback_saves_integration():
    app = _make_app()

    with (
        patch("api.routes.oauth.get_settings") as mock_settings,
        patch("api.routes.oauth._pop_state", new=AsyncMock(return_value="org-1")),
        patch(
            "api.routes.oauth._exchange_slack_code",
            new=AsyncMock(
                return_value={
                    "access_token": "xoxb-tok",
                    "incoming_webhook": {"channel": "C123", "url": "https://hooks.slack.com/x"},
                }
            ),
        ),
        patch("api.routes.oauth._save_integration", new=AsyncMock()),
        patch("api.routes.oauth.encrypt", side_effect=lambda v: f"enc:{v}"),
    ):
        mock_settings.return_value.app_base_url = "https://app.example.com"

        async def run():
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                return await client.get("/api/v1/oauth/slack/callback?code=abc&state=nonce123")

        resp = asyncio.run(run())

    assert resp.status_code == 200
    assert resp.json() == {"status": "connected"}


def test_slack_callback_invalid_state_returns_400():
    app = _make_app()

    with (
        patch("api.routes.oauth.get_settings"),
        patch("api.routes.oauth._pop_state", new=AsyncMock(return_value=None)),
    ):

        async def run():
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                return await client.get("/api/v1/oauth/slack/callback?code=abc&state=bad")

        resp = asyncio.run(run())

    assert resp.status_code == 400


# ─── Notion ───────────────────────────────────────────────────────────────────


def test_notion_authorize_redirects():
    app = _make_app()

    with (
        patch("api.routes.oauth.get_settings") as mock_settings,
        patch("api.routes.oauth._store_state", new=AsyncMock()),
    ):
        mock_settings.return_value.notion_client_id = "NOTION_ID"
        mock_settings.return_value.app_base_url = "https://app.example.com"

        async def run():
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                return await client.get("/api/v1/oauth/notion/authorize?org_id=org-1", follow_redirects=False)

        resp = asyncio.run(run())

    assert resp.status_code == 302
    assert "notion.com/v1/oauth/authorize" in resp.headers["location"]


def test_notion_callback_saves_integration():
    app = _make_app()

    with (
        patch("api.routes.oauth.get_settings") as mock_settings,
        patch("api.routes.oauth._pop_state", new=AsyncMock(return_value="org-1")),
        patch(
            "api.routes.oauth._exchange_notion_code",
            new=AsyncMock(
                return_value={
                    "access_token": "secret_tok",
                    "workspace_id": "ws-1",
                }
            ),
        ),
        patch("api.routes.oauth._save_integration", new=AsyncMock()),
        patch("api.routes.oauth.encrypt", side_effect=lambda v: f"enc:{v}"),
    ):
        mock_settings.return_value.app_base_url = "https://app.example.com"

        async def run():
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                return await client.get("/api/v1/oauth/notion/callback?code=abc&state=nonce456")

        resp = asyncio.run(run())

    assert resp.status_code == 200
    assert resp.json() == {"status": "connected"}


def test_notion_callback_invalid_state_returns_400():
    app = _make_app()

    with (
        patch("api.routes.oauth.get_settings"),
        patch("api.routes.oauth._pop_state", new=AsyncMock(return_value=None)),
    ):

        async def run():
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                return await client.get("/api/v1/oauth/notion/callback?code=abc&state=bad")

        resp = asyncio.run(run())

    assert resp.status_code == 400
