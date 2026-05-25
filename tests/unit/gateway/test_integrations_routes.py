from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch  # noqa: F401

import pytest
from api.routes.integrations import router
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient


def _make_app() -> FastAPI:
    app = FastAPI()
    app.include_router(router)
    return app


def _integration(id: str = "int-1", kind: str = "slack", enabled: bool = True) -> MagicMock:
    i = MagicMock()
    i.id = id
    i.kind = kind
    i.enabled = enabled
    i.config = {"webhook_url": "https://hooks.slack.com/x"}
    i.created_at = None
    i.updated_at = None
    return i


def _session_returning(items) -> tuple[AsyncMock, AsyncMock]:
    session = AsyncMock()
    result = MagicMock()
    result.scalars.return_value.all.return_value = items
    result.scalars.return_value.first.return_value = items[0] if items else None
    result.scalar_one_or_none.return_value = items[0] if items else None
    session.execute.return_value = result
    ctx = AsyncMock()
    ctx.__aenter__ = AsyncMock(return_value=session)
    ctx.__aexit__ = AsyncMock(return_value=False)
    return ctx, session


def _notion_integration(database_id: str | None = None) -> MagicMock:
    i = MagicMock()
    i.id = "int-notion"
    i.kind = "notion"
    i.enabled = True
    i.config = {"token": "enc:secret_tok", "workspace_id": "ws-1"}
    if database_id:
        i.config["database_id"] = database_id
    i.created_at = None
    i.updated_at = None
    return i


def _request_state(org_id: str = "org-1"):
    """Dependency override that injects org_id into request.state."""

    async def _override(request):
        request.state.org_id = org_id
        return org_id

    return _override


@pytest.mark.asyncio
async def test_list_integrations_returns_masked_config():
    app = _make_app()
    ctx, _ = _session_returning([_integration()])

    from api.routes.integrations import _get_org_id

    app.dependency_overrides[_get_org_id] = lambda: "org-1"

    with patch("api.routes.integrations.session_context", return_value=ctx):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/orgs/org-1/integrations")

    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["config"]["webhook_url"] == "***"


@pytest.mark.asyncio
async def test_list_integrations_forbidden_for_other_org():
    app = _make_app()
    from api.routes.integrations import _get_org_id

    app.dependency_overrides[_get_org_id] = lambda: "org-other"

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/orgs/org-1/integrations")

    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_patch_integration_returns_updated():
    app = _make_app()
    existing = _integration()
    ctx, _ = _session_returning([existing])

    from api.routes.integrations import _get_org_id

    app.dependency_overrides[_get_org_id] = lambda: "org-1"

    with patch("api.routes.integrations.session_context", return_value=ctx):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.patch(
                "/orgs/org-1/integrations/int-1",
                json={"enabled": False},
            )

    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_patch_integration_404_when_not_found():
    app = _make_app()
    ctx, _ = _session_returning([])

    from api.routes.integrations import _get_org_id

    app.dependency_overrides[_get_org_id] = lambda: "org-1"

    with patch("api.routes.integrations.session_context", return_value=ctx):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.patch(
                "/orgs/org-1/integrations/missing",
                json={"enabled": False},
            )

    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_integration_returns_204():
    app = _make_app()
    existing = _integration()
    ctx, _ = _session_returning([existing])

    from api.routes.integrations import _get_org_id

    app.dependency_overrides[_get_org_id] = lambda: "org-1"

    with patch("api.routes.integrations.session_context", return_value=ctx):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.delete("/orgs/org-1/integrations/int-1")

    assert resp.status_code == 204


@pytest.mark.asyncio
async def test_delete_integration_404_when_not_found():
    app = _make_app()
    ctx, _ = _session_returning([])

    from api.routes.integrations import _get_org_id

    app.dependency_overrides[_get_org_id] = lambda: "org-1"

    with patch("api.routes.integrations.session_context", return_value=ctx):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.delete("/orgs/org-1/integrations/missing")

    assert resp.status_code == 404


# ─── Notion database selection ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_notion_databases_returns_list():
    app = _make_app()
    ctx, _ = _session_returning([_notion_integration()])

    from api.routes.integrations import _get_org_id

    app.dependency_overrides[_get_org_id] = lambda: "org-1"

    notion_resp = MagicMock()
    notion_resp.raise_for_status = MagicMock()
    notion_resp.json.return_value = {
        "results": [
            {"id": "db-abc", "title": [{"plain_text": "Reviews DB"}]},
            {"id": "db-xyz", "title": [{"plain_text": "Bugs DB"}]},
        ]
    }

    with (
        patch("api.routes.integrations.session_context", return_value=ctx),
        patch("api.routes.integrations.decrypt", return_value="secret_tok"),
        patch("api.routes.integrations.httpx.AsyncClient") as mock_client_cls,
    ):
        mock_http = AsyncMock()
        mock_http.post = AsyncMock(return_value=notion_resp)
        mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_http)
        mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/orgs/org-1/integrations/notion/databases")

    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
    assert data[0] == {"id": "db-abc", "title": "Reviews DB"}
    assert data[1] == {"id": "db-xyz", "title": "Bugs DB"}


@pytest.mark.asyncio
async def test_list_notion_databases_404_when_not_connected():
    app = _make_app()
    ctx, _ = _session_returning([])

    from api.routes.integrations import _get_org_id

    app.dependency_overrides[_get_org_id] = lambda: "org-1"

    with patch("api.routes.integrations.session_context", return_value=ctx):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/orgs/org-1/integrations/notion/databases")

    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_select_notion_database_saves_id():
    app = _make_app()
    notion_int = _notion_integration()
    ctx, _ = _session_returning([notion_int])

    from api.routes.integrations import _get_org_id

    app.dependency_overrides[_get_org_id] = lambda: "org-1"

    with patch("api.routes.integrations.session_context", return_value=ctx):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.patch(
                "/orgs/org-1/integrations/notion/database",
                json={"database_id": "db-abc"},
            )

    assert resp.status_code == 200
    assert resp.json() == {"status": "ok", "database_id": "db-abc"}
    assert notion_int.config["database_id"] == "db-abc"


@pytest.mark.asyncio
async def test_select_notion_database_404_when_not_connected():
    app = _make_app()
    ctx, _ = _session_returning([])

    from api.routes.integrations import _get_org_id

    app.dependency_overrides[_get_org_id] = lambda: "org-1"

    with patch("api.routes.integrations.session_context", return_value=ctx):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.patch(
                "/orgs/org-1/integrations/notion/database",
                json={"database_id": "db-abc"},
            )

    assert resp.status_code == 404
