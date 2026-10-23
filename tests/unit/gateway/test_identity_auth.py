"""Sign-in, sign-up and account linking across providers, against a real (in-memory) database."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from api.routes import auth as auth_routes
from fastapi import FastAPI
from fastapi.testclient import TestClient
from identity_providers import Profile
from shared.db import get_session
from shared.models import AuthIdentity, Org, OrgBilling, OrgInvite, User, UserOrg
from sqlalchemy import func, select


class FakeProvider:
    def __init__(self, name="github", host="", label=None, profile=None):
        self.name, self.host, self.label = name, host, label or name.title()
        self.profile = profile or Profile("1", "alice", "Alice A", "http://a/v.png", "alice@x.io", frozenset({"alice@x.io"}))

    def authorize_url(self, state: str) -> str:
        return f"https://idp.test/authorize?state={state}"

    async def fetch_profile(self, client, code):
        return self.profile


GITHUB = FakeProvider("github")
GITLAB = FakeProvider("gitlab", host="https://gitlab.com")


def profile(subject="1", login="alice", emails=("alice@x.io",)):
    return Profile(subject, login, login.title(), None, emails[0] if emails else None, frozenset(emails))


async def count(session, model):
    return await session.scalar(select(func.count()).select_from(model))


# ── data layer ───────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_first_sign_in_creates_user_identity_personal_org_and_billing(session):
    user, org, membership = await auth_routes._login_or_signup(session, GITLAB, profile("42", "bob"))

    assert (user.login, org.slug, membership.role) == ("bob", "bob", "owner")
    identity = (await session.execute(select(AuthIdentity))).scalar_one()
    assert (identity.provider, identity.provider_host, identity.provider_user_id) == ("gitlab", "https://gitlab.com", "42")
    assert await count(session, OrgBilling) == 1


@pytest.mark.asyncio
async def test_repeat_sign_in_reuses_account_and_refreshes_login(session):
    first, *_ = await auth_routes._login_or_signup(session, GITHUB, profile("7", "carol"))
    again, org, _ = await auth_routes._login_or_signup(session, GITHUB, profile("7", "carol-renamed"))

    assert again.id == first.id
    assert (await count(session, User), await count(session, Org)) == (1, 1)
    assert (await session.execute(select(AuthIdentity.login))).scalar_one() == "carol-renamed"


@pytest.mark.asyncio
async def test_same_login_on_two_providers_gets_distinct_users_and_slugs(session):
    gh, gh_org, _ = await auth_routes._login_or_signup(session, GITHUB, profile("1", "dave"))
    gl, gl_org, _ = await auth_routes._login_or_signup(session, GITLAB, profile("9", "dave"))

    assert gh.id != gl.id
    assert (gh_org.slug, gl_org.slug) == ("dave", "dave-gitlab")


@pytest.mark.asyncio
async def test_slug_falls_back_to_random_suffix_when_hint_also_taken(session):
    session.add_all([Org(slug="erin", name="x"), Org(slug="erin-gitlab", name="y")])
    await session.commit()

    slug = await auth_routes.unique_org_slug(session, "erin", "gitlab")

    assert slug.startswith("erin-") and slug not in {"erin", "erin-gitlab"}


@pytest.mark.asyncio
async def test_linking_unifies_accounts_across_providers(session):
    user, org, _ = await auth_routes._login_or_signup(session, GITHUB, profile("1", "frank"))

    assert await auth_routes._link_identity(session, user.id, GITLAB, profile("55", "frank-gl")) == "ok"
    again, same_org, _ = await auth_routes._login_or_signup(session, GITLAB, profile("55", "frank-gl"))

    assert (again.id, same_org.id) == (user.id, org.id)
    assert await count(session, User) == 1


@pytest.mark.asyncio
async def test_link_rules(session):
    a, *_ = await auth_routes._login_or_signup(session, GITHUB, profile("1", "gina"))
    b, *_ = await auth_routes._login_or_signup(session, GITLAB, profile("2", "hank"))

    assert await auth_routes._link_identity(session, a.id, GITHUB, profile("1", "gina")) == "ok"  # idempotent
    assert await auth_routes._link_identity(session, a.id, GITLAB, profile("2", "hank")) == "already_linked"  # someone else's
    assert await auth_routes._link_identity(session, a.id, GITHUB, profile("3", "gina-2")) == "provider_taken"  # 2nd github
    assert await count(session, AuthIdentity) == 2


async def _invite(session, org_id, user_id, email="alice@x.io", seats=3):
    billing = (await session.execute(select(OrgBilling).where(OrgBilling.org_id == org_id))).scalar_one()
    billing.seat_count = seats
    inv = OrgInvite(org_id=org_id, email=email, invited_by=user_id)
    session.add(inv)
    await session.commit()
    return inv


@pytest.mark.asyncio
async def test_invite_accepted_with_any_verified_email_from_any_provider(session):
    owner, org, _ = await auth_routes._login_or_signup(session, GITHUB, profile("1", "owner", ("o@x.io",)))
    invitee, *_ = await auth_routes._login_or_signup(session, GITLAB, profile("2", "ivy", ("ivy@corp.io",)))
    inv = await _invite(session, org.id, owner.id, email="Ivy@Corp.io")

    assert await auth_routes._consume_invite(session, invitee.id, inv.token, {"ivy@corp.io"}) == (org.id, "member")
    assert await count(session, UserOrg) == 3  # two personal owners + the new member


@pytest.mark.asyncio
async def test_invite_rejected_for_other_email_and_when_seats_full(session):
    owner, org, _ = await auth_routes._login_or_signup(session, GITHUB, profile("1", "owner", ("o@x.io",)))
    invitee, *_ = await auth_routes._login_or_signup(session, GITHUB, profile("2", "ivy", ("ivy@corp.io",)))
    inv = await _invite(session, org.id, owner.id, email="ivy@corp.io", seats=1)

    assert await auth_routes._consume_invite(session, invitee.id, inv.token, {"mallory@x.io"}) is None
    assert await auth_routes._consume_invite(session, invitee.id, inv.token, {"ivy@corp.io"}) is None  # 1 seat, owner holds it
    assert inv.accepted_at is None


@pytest.mark.asyncio
async def test_expired_invite_rejected(session):
    owner, org, _ = await auth_routes._login_or_signup(session, GITHUB, profile("1", "owner", ("o@x.io",)))
    inv = await _invite(session, org.id, owner.id, email="o@x.io")
    inv.expires_at = datetime.now(timezone.utc) - timedelta(days=1)
    await session.commit()

    assert await auth_routes._consume_invite(session, owner.id, inv.token, {"o@x.io"}) is None


# ── HTTP layer ───────────────────────────────────────────────────────────────


def make_client(session, providers, redis, user_id=None):
    app = FastAPI()
    app.include_router(auth_routes.router, prefix="/api/v1/auth")
    app.state.redis = redis

    async def _session():
        yield session

    app.dependency_overrides[get_session] = _session

    if user_id:

        @app.middleware("http")
        async def _auth(request, call_next):
            request.state.user_id = user_id
            return await call_next(request)

    patcher = patch.object(auth_routes, "get_providers", return_value=providers)
    patcher.start()
    return TestClient(app, follow_redirects=False), patcher


def redis_with_state(state_obj):
    r = MagicMock()
    r.set = AsyncMock()
    r.getdel = AsyncMock(return_value=json.dumps(state_obj))
    return r


def test_providers_endpoint_and_unknown_provider(session):
    client, p = make_client(session, {"github": GITHUB}, redis_with_state({}))
    try:
        assert client.get("/api/v1/auth/providers").json() == [{"id": "github", "label": "Github", "host": ""}]
        assert client.get("/api/v1/auth/gitlab/login").status_code == 404  # not configured here
    finally:
        p.stop()


def test_login_redirects_to_provider_with_state_carrying_invite(session):
    redis = redis_with_state({})
    client, p = make_client(session, {"gitlab": GITLAB}, redis)
    try:
        resp = client.get("/api/v1/auth/gitlab/login?invite_token=inv-1")
    finally:
        p.stop()

    assert resp.status_code in (302, 307) and resp.headers["location"].startswith("https://idp.test/authorize?state=")
    assert json.loads(redis.set.call_args[0][1]) == {"cli": "", "invite": "inv-1"}


@pytest.mark.asyncio
async def test_callback_signs_up_new_gitlab_user_and_hands_off_cookie_nonce(session):
    redis = redis_with_state({"cli": "", "invite": "", "link": ""})
    client, p = make_client(session, {"gitlab": GitLabWithProfile()}, redis)
    try:
        resp = client.get("/api/v1/auth/gitlab/callback?code=c&state=s")
    finally:
        p.stop()

    assert resp.status_code == 302
    assert "/auth/callback#token=" in resp.headers["location"] and "&nonce=" in resp.headers["location"]
    assert redis.set.call_args[0][0].startswith("cookie_nonce:")
    assert await count(session, User) == 1


def GitLabWithProfile():
    return FakeProvider("gitlab", host="https://gitlab.com", profile=profile("77", "newbie"))


@pytest.mark.asyncio
async def test_link_callback_requires_matching_browser_cookie(session):
    user, *_ = await auth_routes._login_or_signup(session, GITHUB, profile("1", "jules"))
    provider = FakeProvider("gitlab", host="https://gitlab.com", profile=profile("88", "jules-gl"))
    state = {"cli": "", "invite": "", "link": user.id}

    client, p = make_client(session, {"gitlab": provider}, redis_with_state(state))
    try:
        no_cookie = client.get("/api/v1/auth/gitlab/callback?code=c&state=s1")
    finally:
        p.stop()
    assert no_cookie.headers["location"].endswith("/dashboard/settings?link_error=state")
    assert await count(session, AuthIdentity) == 1

    client, p = make_client(session, {"gitlab": provider}, redis_with_state(state))
    try:
        client.cookies.set("argus_link_state", "s2")
        ok = client.get("/api/v1/auth/gitlab/callback?code=c&state=s2")
    finally:
        p.stop()
    assert ok.headers["location"].endswith("/dashboard/settings?linked=gitlab")
    assert await count(session, AuthIdentity) == 2


def test_link_start_sets_binding_cookie(session):
    redis = redis_with_state({})
    client, p = make_client(session, {"gitlab": GITLAB}, redis, user_id="u-1")
    try:
        resp = client.get("/api/v1/auth/link/gitlab")
    finally:
        p.stop()

    state = json.loads(redis.set.call_args[0][1])
    assert state["link"] == "u-1"
    assert "argus_link_state=" in resp.headers["set-cookie"] and "HttpOnly" in resp.headers["set-cookie"]


@pytest.mark.asyncio
async def test_unlink_requires_another_sign_in_method(session):
    user, *_ = await auth_routes._login_or_signup(session, GITHUB, profile("1", "kim"))
    only = (await session.execute(select(AuthIdentity))).scalar_one()
    client, p = make_client(session, {"github": GITHUB}, redis_with_state({}), user_id=user.id)
    try:
        assert client.delete(f"/api/v1/auth/identities/{only.id}").status_code == 400

        await auth_routes._link_identity(session, user.id, GITLAB, profile("2", "kim-gl"))
        listed = client.get("/api/v1/auth/identities").json()
        assert sorted(i["provider"] for i in listed) == ["github", "gitlab"]
        assert client.delete(f"/api/v1/auth/identities/{only.id}").status_code == 204
        assert client.delete(f"/api/v1/auth/identities/{only.id}").status_code == 404
    finally:
        p.stop()
