from unittest.mock import AsyncMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from middleware.rate_limit import RateLimitMiddleware


def _make_app():
    app = FastAPI()
    app.add_middleware(RateLimitMiddleware)

    @app.post("/api/v1/webhooks/github")
    def webhook():
        return {"ok": True}

    return app


def test_under_limit_passes():
    with patch("middleware.rate_limit.get_redis") as mock_r:
        mock_redis = AsyncMock()
        mock_redis.incr.return_value = 1
        mock_redis.expire = AsyncMock()
        mock_r.return_value = mock_redis
        client = TestClient(_make_app())
        resp = client.post("/api/v1/webhooks/github", headers={"X-Installation-Id": "123"})
        assert resp.status_code == 200


def test_over_limit_returns_429():
    with patch("middleware.rate_limit.get_redis") as mock_r:
        mock_redis = AsyncMock()
        mock_redis.incr.return_value = 61  # over limit of 60
        mock_redis.expire = AsyncMock()
        mock_r.return_value = mock_redis
        client = TestClient(_make_app())
        resp = client.post("/api/v1/webhooks/github", headers={"X-Installation-Id": "123"})
        assert resp.status_code == 429
