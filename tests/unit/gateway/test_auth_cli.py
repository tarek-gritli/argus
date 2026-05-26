from unittest.mock import AsyncMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient


def _make_app():
    from api.routes.auth_cli import router

    app = FastAPI()
    app.include_router(router, prefix="/api/v1/auth/cli")
    app.state.redis = AsyncMock()
    return app


def test_create_session_returns_session_id_and_url():
    app = _make_app()
    app.state.redis.set = AsyncMock()
    client = TestClient(app)
    with patch("api.routes.auth_cli.get_settings") as mock_settings:
        mock_settings.return_value.app_base_url = "http://localhost:8000"
        mock_settings.return_value.api_prefix = "/api/v1"
        resp = client.post("/api/v1/auth/cli/session")
    assert resp.status_code == 200
    data = resp.json()
    assert "session_id" in data
    assert "browser_url" in data
    assert "cli_session_id=" in data["browser_url"]


def test_poll_token_pending_returns_202():
    app = _make_app()
    app.state.redis.getdel = AsyncMock(return_value=None)
    client = TestClient(app)
    resp = client.get("/api/v1/auth/cli/token/some-session-id")
    assert resp.status_code == 202


def test_poll_token_ready_returns_200_with_token():
    app = _make_app()
    app.state.redis.getdel = AsyncMock(return_value="jwt_token_value")
    client = TestClient(app)
    resp = client.get("/api/v1/auth/cli/token/some-session-id")
    assert resp.status_code == 200
    assert resp.json()["token"] == "jwt_token_value"
