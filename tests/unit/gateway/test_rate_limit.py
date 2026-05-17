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


def _make_redis(evalsha_result):
    mock_redis = AsyncMock()
    mock_redis.evalsha = AsyncMock(return_value=evalsha_result)
    mock_redis.script_load = AsyncMock(return_value="fakeshaa")
    mock_redis.exists = AsyncMock(return_value=1)
    return mock_redis


def test_under_limit_passes():
    # evalsha returns [allowed=1, remaining=59]
    with patch("middleware.rate_limit.get_redis", return_value=_make_redis([1, 59])):
        client = TestClient(_make_app())
        resp = client.post("/api/v1/webhooks/github", headers={"X-Installation-Id": "123"})
    assert resp.status_code == 200


def test_over_limit_returns_429():
    # evalsha returns [allowed=0, remaining=0]
    with patch("middleware.rate_limit.get_redis", return_value=_make_redis([0, 0])):
        client = TestClient(_make_app())
        resp = client.post("/api/v1/webhooks/github", headers={"X-Installation-Id": "123"})
    assert resp.status_code == 429


def test_non_webhook_path_skips_rate_limit():
    with patch("middleware.rate_limit.get_redis") as mock_get_redis:
        app = FastAPI()
        app.add_middleware(RateLimitMiddleware)

        @app.get("/health")
        def health():
            return {"ok": True}

        client = TestClient(app)
        resp = client.get("/health")

    assert resp.status_code == 200
    mock_get_redis.assert_not_called()


def test_redis_outage_allows_request():
    mock_redis = AsyncMock()
    mock_redis.evalsha = AsyncMock(side_effect=Exception("Redis down"))
    mock_redis.script_load = AsyncMock(side_effect=Exception("Redis down"))
    with patch("middleware.rate_limit.get_redis", return_value=mock_redis):
        client = TestClient(_make_app())
        resp = client.post("/api/v1/webhooks/github", headers={"X-Installation-Id": "123"})
    assert resp.status_code == 200


def test_noscript_reloads_and_retries():
    # First evalsha raises NOSCRIPT; after reload the retry succeeds.
    mock_redis = AsyncMock()
    mock_redis.script_load = AsyncMock(return_value="newsha")
    mock_redis.evalsha = AsyncMock(side_effect=[Exception("NOSCRIPT No matching script"), [1, 59]])
    with patch("middleware.rate_limit.get_redis", return_value=mock_redis):
        client = TestClient(_make_app())
        resp = client.post("/api/v1/webhooks/github", headers={"X-Installation-Id": "123"})
    assert resp.status_code == 200
    assert mock_redis.script_load.call_count == 2  # initial load + reload


def test_burst_allowed_within_capacity():
    # Simulates 3 rapid events (GitHub PR open/sync/reopen) — all should pass
    results = [[1, 59], [1, 58], [1, 57]]
    call_count = 0

    async def evalsha_side_effect(*args, **kwargs):
        nonlocal call_count
        r = results[call_count]
        call_count += 1
        return r

    mock_redis = AsyncMock()
    mock_redis.evalsha = AsyncMock(side_effect=evalsha_side_effect)
    mock_redis.script_load = AsyncMock(return_value="fakeshaa")

    with patch("middleware.rate_limit.get_redis", return_value=mock_redis):
        client = TestClient(_make_app())
        for _ in range(3):
            resp = client.post("/api/v1/webhooks/github", headers={"X-Installation-Id": "123"})
            assert resp.status_code == 200
