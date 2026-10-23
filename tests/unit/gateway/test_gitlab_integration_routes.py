from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from api.routes.integrations import router
from fastapi import FastAPI, Request
from gitlab.exceptions import GitlabAuthenticationError
from httpx import ASGITransport, AsyncClient
from integrations.gitlab import InvalidGitLabURL
from shared.crypto import decrypt
from shared.models.org_integration import OrgIntegration


def _app(role: str = "owner", org_id: str = "org-1") -> FastAPI:
    app = FastAPI()
    app.include_router(router)

    @app.middleware("http")
    async def _auth(request: Request, call_next):  # stands in for AuthMiddleware
        request.state.org_id, request.state.role = org_id, role
        return await call_next(request)

    return app


def _db(session=None):
    session = session or AsyncMock()
    session.add = MagicMock()
    ctx = AsyncMock()
    ctx.__aenter__ = AsyncMock(return_value=session)
    ctx.__aexit__ = AsyncMock(return_value=False)
    return ctx, session


async def _connect(app, body=None):
    body = body or {"base_url": "https://git.corp.io", "access_token": "glpat-x"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        return await client.post("/orgs/org-1/integrations/gitlab", json=body)


@pytest.mark.asyncio
async def test_connect_requires_owner():
    with patch("api.routes.integrations._verify_gitlab_token") as verify:
        resp = await _connect(_app(role="member"))
    assert resp.status_code == 403
    verify.assert_not_called()


@pytest.mark.asyncio
async def test_connect_rejects_other_orgs():
    assert (await _connect(_app(org_id="someone-else"))).status_code == 403


@pytest.mark.asyncio
async def test_connect_rejects_unsafe_url():
    with patch("api.routes.integrations._verify_gitlab_token", side_effect=InvalidGitLabURL("non-public")):
        resp = await _connect(_app())
    assert resp.status_code == 400
    assert "non-public" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_connect_rejects_bad_token_and_stores_nothing():
    ctx, session = _db()
    with (
        patch("api.routes.integrations._verify_gitlab_token", side_effect=GitlabAuthenticationError("401", 401)),
        patch("api.routes.integrations.session_context", return_value=ctx),
    ):
        resp = await _connect(_app())
    assert resp.status_code == 400
    session.add.assert_not_called()


@pytest.mark.asyncio
async def test_connect_unreachable_instance_is_502():
    with patch("api.routes.integrations._verify_gitlab_token", side_effect=OSError("timeout")):
        assert (await _connect(_app())).status_code == 502


@pytest.mark.asyncio
async def test_connect_stores_encrypted_secrets_and_returns_webhook_details_once():
    ctx, session = _db()

    async def commit():
        session.add.call_args.args[0].id = "int-9"

    session.commit = AsyncMock(side_effect=commit)
    with (
        patch("api.routes.integrations._verify_gitlab_token"),
        patch("api.routes.integrations.session_context", return_value=ctx),
        patch("api.routes.integrations.normalize_base_url", return_value="https://git.corp.io"),
    ):
        resp = await _connect(_app())

    assert resp.status_code == 201
    data = resp.json()
    assert data["id"] == "int-9"
    assert data["webhook_url"].endswith("/api/v1/webhooks/gitlab/int-9")

    saved: OrgIntegration = session.add.call_args.args[0]
    assert (saved.org_id, saved.kind) == ("org-1", "gitlab")
    assert saved.config["base_url"] == "https://git.corp.io"
    assert saved.config["access_token"] != "glpat-x" and decrypt(saved.config["access_token"]) == "glpat-x"
    assert decrypt(saved.config["webhook_secret"]) == data["webhook_secret"]
    assert data["webhook_secret"] not in str(saved.config)


@pytest.mark.asyncio
async def test_rotate_secret_replaces_stored_secret():
    integration = OrgIntegration(org_id="org-1", kind="gitlab", config={"webhook_secret": "old"}, id="int-1")
    session = AsyncMock()
    session.execute.return_value = MagicMock(scalar_one_or_none=MagicMock(return_value=integration))
    ctx, _ = _db(session)

    with patch("api.routes.integrations.session_context", return_value=ctx):
        async with AsyncClient(transport=ASGITransport(app=_app()), base_url="http://test") as client:
            resp = await client.post("/orgs/org-1/integrations/int-1/gitlab/rotate-secret")

    assert resp.status_code == 200
    assert decrypt(integration.config["webhook_secret"]) == resp.json()["webhook_secret"]
    assert integration.config["webhook_secret"] != "old"
