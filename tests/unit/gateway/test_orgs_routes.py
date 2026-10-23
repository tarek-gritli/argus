from unittest.mock import AsyncMock, MagicMock

import jwt
import pytest
from api.routes import auth as auth_routes
from api.routes import orgs as orgs_routes
from fastapi import FastAPI
from fastapi.testclient import TestClient
from identity_providers import Profile
from shared.db import get_session
from shared.models import Org, OrgBilling, UserOrg
from sqlalchemy import func, select


class _Gh:
    name, host, label = "github", "", "GitHub"


async def _user(session, subject="1", login="zed"):
    user, org, _ = await auth_routes._login_or_signup(session, _Gh(), Profile(subject, login, None, None))
    return user, org


def _client(session, user_id, org_id):
    app = FastAPI()
    app.include_router(orgs_routes.router)
    redis = MagicMock()
    redis.set = AsyncMock()
    app.state.redis = redis

    async def _session():
        yield session

    app.dependency_overrides[get_session] = _session

    @app.middleware("http")
    async def _auth(request, call_next):
        request.state.user_id, request.state.org_id = user_id, org_id
        return await call_next(request)

    return TestClient(app), redis


@pytest.mark.asyncio
async def test_user_can_create_additional_orgs_they_own(session):
    user, personal = await _user(session)
    client, _ = _client(session, user.id, personal.id)

    resp = client.post("/orgs", json={"name": "Acme Platform Team"})

    assert resp.status_code == 201
    assert resp.json()["slug"] == "acme-platform-team" and resp.json()["role"] == "owner"
    orgs = client.get("/orgs").json()
    assert [o["name"] for o in orgs] == ["zed", "Acme Platform Team"]
    assert [o["current"] for o in orgs] == [True, False]
    new_org = (await session.execute(select(Org).where(Org.slug == "acme-platform-team"))).scalar_one()
    assert (await session.execute(select(OrgBilling).where(OrgBilling.org_id == new_org.id))).scalar_one().plan == "free"


@pytest.mark.asyncio
async def test_owned_org_cap(session):
    user, personal = await _user(session)
    client, _ = _client(session, user.id, personal.id)

    for i in range(orgs_routes.MAX_OWNED_ORGS - 1):
        assert client.post("/orgs", json={"name": f"team {i}"}).status_code == 201
    assert client.post("/orgs", json={"name": "one too many"}).status_code == 403
    assert await session.scalar(select(func.count()).where(UserOrg.user_id == user.id)) == orgs_routes.MAX_OWNED_ORGS


@pytest.mark.asyncio
async def test_rejects_bad_names(session):
    user, personal = await _user(session)
    client, _ = _client(session, user.id, personal.id)
    assert client.post("/orgs", json={"name": " x "}).status_code == 422


@pytest.mark.asyncio
async def test_switch_issues_token_for_member_org_with_nonce_and_refuses_strangers(session):
    user, personal = await _user(session)
    other, other_org = await _user(session, "2", "other")
    client, redis = _client(session, user.id, personal.id)
    team = client.post("/orgs", json={"name": "Team"}).json()

    ok = client.post(f"/orgs/{team['id']}/switch")
    assert ok.status_code == 200
    claims = jwt.decode(ok.json()["token"], options={"verify_signature": False})
    assert (claims["sub"], claims["oid"], claims["role"]) == (user.id, team["id"], "owner")
    assert redis.set.call_args[0][0] == f"cookie_nonce:{ok.json()['nonce']}"

    assert client.post(f"/orgs/{other_org.id}/switch").status_code == 404
