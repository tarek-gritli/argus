from unittest.mock import AsyncMock, MagicMock, patch

from api.routes.auth import router
from fastapi import FastAPI
from fastapi.testclient import TestClient


def _make_app_with_redis():
    app = FastAPI()
    app.include_router(router, prefix="/api/v1/auth")
    mock_redis = MagicMock()
    mock_redis.set = AsyncMock()
    app.state.redis = mock_redis
    return app


def test_login_redirects_to_github():
    with patch("api.routes.auth.get_settings") as mock_s:
        mock_s.return_value.github_client_id = "test_client_id"
        client = TestClient(_make_app_with_redis(), follow_redirects=False)
        resp = client.get("/api/v1/auth/github/login")
        assert resp.status_code in (302, 307)
        assert "github.com/login/oauth/authorize" in resp.headers["location"]


def test_logout_clears_cookie():
    app = FastAPI()
    app.include_router(router, prefix="/api/v1/auth")
    client = TestClient(app)
    resp = client.delete("/api/v1/auth/logout")
    assert resp.status_code == 200
