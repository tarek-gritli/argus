"""Changing an org's integrations is owner-only; members can still read them."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from api.routes import integrations, oauth
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

GUARDED = [
    ("PATCH", "/orgs/org-1/integrations/int-1", {"enabled": False}),
    ("DELETE", "/orgs/org-1/integrations/int-1", None),
    ("GET", "/orgs/org-1/integrations/int-1/notion/databases", None),
    ("PATCH", "/orgs/org-1/integrations/int-1/notion/database", {"database_id": "db"}),
    ("POST", "/orgs/org-1/integrations/gitlab", {"base_url": "https://gitlab.com", "access_token": "t"}),
    ("POST", "/orgs/org-1/integrations/int-1/gitlab/rotate-secret", None),
    ("GET", "/oauth/slack/authorize?org_id=org-1", None),
    ("GET", "/oauth/notion/authorize?org_id=org-1", None),
    ("GET", "/oauth/linear/authorize?org_id=org-1", None),
    ("GET", "/oauth/jira/authorize?org_id=org-1", None),
]


def _app(role) -> FastAPI:
    app = FastAPI()
    app.state.redis = AsyncMock()
    app.include_router(integrations.router)
    app.include_router(oauth.router, prefix="/oauth")

    @app.middleware("http")
    async def _auth(request, call_next):
        request.state.org_id = "org-1"
        if role is not None:
            request.state.role = role
        return await call_next(request)

    return app


async def _call(app, method, path, body):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test", follow_redirects=False) as client:
        return await client.request(method, path, json=body)


@pytest.mark.asyncio
@pytest.mark.parametrize("role", ["member", "viewer", None], ids=["member", "unknown-role", "no-role"])
@pytest.mark.parametrize("method, path, body", GUARDED, ids=[f"{m} {p.split('?')[0]}" for m, p, _ in GUARDED])
async def test_non_owners_are_rejected_before_any_work(role, method, path, body):
    boom = MagicMock(side_effect=AssertionError("DB/Redis touched by a non-owner request"))
    with patch("api.routes.integrations.session_context", boom), patch("api.routes.oauth.session_context", boom):
        resp = await _call(_app(role), method, path, body)

    assert resp.status_code == 403
    assert "owner" in resp.json()["detail"].lower()
    boom.assert_not_called()


@pytest.mark.asyncio
async def test_members_can_still_list_integrations():
    session = AsyncMock()
    session.execute.return_value = MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[]))))
    ctx = AsyncMock()
    ctx.__aenter__ = AsyncMock(return_value=session)
    ctx.__aexit__ = AsyncMock(return_value=False)

    with patch("api.routes.integrations.session_context", return_value=ctx):
        resp = await _call(_app("member"), "GET", "/orgs/org-1/integrations", None)

    assert resp.status_code == 200 and resp.json() == []


@pytest.mark.asyncio
async def test_owner_passes_the_guard():
    ctx = AsyncMock()
    session = AsyncMock()
    session.execute.return_value = MagicMock(scalar_one_or_none=MagicMock(return_value=None))
    ctx.__aenter__ = AsyncMock(return_value=session)
    ctx.__aexit__ = AsyncMock(return_value=False)

    with patch("api.routes.integrations.session_context", return_value=ctx):
        resp = await _call(_app("owner"), "DELETE", "/orgs/org-1/integrations/int-1", None)

    assert resp.status_code == 404  # got past the guard; the integration just doesn't exist
