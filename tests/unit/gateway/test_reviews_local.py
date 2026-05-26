import json
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient


def _make_app():
    from api.routes.reviews_local import router

    app = FastAPI()
    app.include_router(router, prefix="/api/v1/reviews/local")
    mock_redis = MagicMock()
    mock_redis.get = AsyncMock(return_value=None)
    app.state.redis = mock_redis
    return app, mock_redis


def test_post_enqueues_and_returns_job_id():
    app, _ = _make_app()
    with patch("api.routes.reviews_local._get_celery") as mock_get_celery:
        mock_celery = MagicMock()
        mock_get_celery.return_value = mock_celery
        client = TestClient(app)
        resp = client.post("/api/v1/reviews/local", json={"diff": "+ some code"})

    assert resp.status_code == 202
    body = resp.json()
    assert "job_id" in body
    assert "stream_url" in body
    assert "status_url" in body
    mock_celery.send_task.assert_called_once()
    assert mock_celery.send_task.call_args[0][0] == "review_local"


def test_get_poll_returns_202_when_pending():
    app, mock_redis = _make_app()
    mock_redis.get = AsyncMock(return_value=None)
    client = TestClient(app)
    resp = client.get("/api/v1/reviews/local/job123")
    assert resp.status_code == 202
    assert resp.json()["status"] == "pending"


def test_get_poll_returns_findings_when_done():
    findings = [{"agent": "security", "severity": "high", "title": "XSS"}]
    app, mock_redis = _make_app()
    mock_redis.get = AsyncMock(return_value=json.dumps(findings).encode())
    client = TestClient(app)
    resp = client.get("/api/v1/reviews/local/job123")
    assert resp.status_code == 200
    assert resp.json()["findings"] == findings


def test_post_empty_diff_returns_400():
    app, _ = _make_app()
    client = TestClient(app)
    resp = client.post("/api/v1/reviews/local", json={"diff": "   "})
    assert resp.status_code == 400
