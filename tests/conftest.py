import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

os.environ["GITHUB_APP_ID"] = "12345"
os.environ["GITHUB_WEBHOOK_SECRET"] = "test-secret"
os.environ["GITHUB_PRIVATE_KEY_B64"] = "dGVzdF9rZXk="
os.environ["REDIS_URL"] = "redis://localhost:6379/15"
os.environ["CELERY_BROKER_URL"] = "redis://localhost:6379/15"
os.environ["GITHUB_CLIENT_ID"] = "github_client_id"
os.environ["GITHUB_CLIENT_SECRET"] = "github_client_secret"
os.environ["JWT_SECRET_KEY"] = "jwt_secret_key"
os.environ["SECRET_ENCRYPTION_KEY"] = "Oy-9hVTGzq-XfkjHqVNmO7wRJQnBdQlEzPMktfVi5dI="


@pytest.fixture
def mock_redis():
    """Mock Redis client with tracking for assertions."""
    mock_r = AsyncMock()
    mock_r.set = AsyncMock(return_value=True)
    mock_r.delete = AsyncMock(return_value=True)
    mock_r.incr = AsyncMock(return_value=1)
    mock_r.expire = AsyncMock(return_value=True)
    mock_r.aclose = AsyncMock()
    yield mock_r


@pytest.fixture
def mock_celery():
    """Mock Celery app with tracking for task assertions."""
    mock_c = MagicMock()
    mock_c.send_task = MagicMock(return_value=None)
    yield mock_c


@pytest.fixture
def mock_session_context():
    """Mock async DB session context manager — prevents real DB connections in unit tests."""
    mock_session = AsyncMock()
    mock_ctx = AsyncMock()
    mock_ctx.__aenter__ = AsyncMock(return_value=mock_session)
    mock_ctx.__aexit__ = AsyncMock(return_value=False)

    mock_get_or_create = AsyncMock(return_value="mock-org-id")

    return mock_ctx, mock_get_or_create


@pytest.fixture
def patch_gateway_deps(mock_redis, mock_celery, mock_session_context):
    """
    Patch Redis, Celery, and DB session, reimport app fresh, and yield with lifespan context.

    Uses FastAPI's TestClient lifespan pattern: the app's lifespan runs when entering
    the 'with TestClient(app)' context and cleans up when exiting.
    """
    mock_ctx, mock_get_or_create = mock_session_context

    # Keep patches active for the entire test duration
    redis_patcher = patch("redis.asyncio.from_url", return_value=mock_redis)
    celery_patcher = patch("celery.Celery", return_value=mock_celery)
    session_patcher = patch("api.routes.webhooks.session_context", return_value=mock_ctx)
    org_patcher = patch("api.routes.webhooks.get_or_create_org", new=mock_get_or_create)

    redis_patcher.start()
    celery_patcher.start()
    session_patcher.start()
    org_patcher.start()

    try:
        from gateway_main import app

        with TestClient(app) as _:
            yield app, mock_redis, mock_celery
    finally:
        redis_patcher.stop()
        celery_patcher.stop()
        session_patcher.stop()
        org_patcher.stop()

        for mod in ["gateway_main", "api", "api.routes", "api.routes.webhooks"]:
            if mod in sys.modules:
                del sys.modules[mod]
