from __future__ import annotations

import secrets

import httpx
from auth_utils import create_jwt
from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from shared.config import Settings, get_settings
from shared.db import get_session
from shared.models import Org, OrgBilling, User, UserOrg
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()

_GITHUB_AUTHORIZE_URL = "https://github.com/login/oauth/authorize"
_GITHUB_TOKEN_URL = "https://github.com/login/oauth/access_token"
_GITHUB_USER_URL = "https://api.github.com/user"
_CSRF_TTL = 600  # 10 minutes
_COOKIE_NONCE_TTL = 300  # 5 minutes


@router.get("/github/login")
async def github_login(
    request: Request,
    cli_session_id: str | None = None,
    settings: Settings = Depends(get_settings),
):
    state = secrets.token_urlsafe(32)
    # Store cli_session_id alongside the CSRF token so the callback can retrieve
    # it — GitHub does not round-trip unknown query params back to the callback.
    state_value = cli_session_id if cli_session_id else "1"
    await request.app.state.redis.set(f"oauth_state:{state}", state_value, ex=_CSRF_TTL)
    url = f"{_GITHUB_AUTHORIZE_URL}?client_id={settings.github_client_id}&state={state}&scope=read:user"
    return RedirectResponse(url=url)


@router.get("/github/callback")
async def github_callback(
    code: str,
    state: str,
    request: Request,
    settings: Settings = Depends(get_settings),
    session: AsyncSession = Depends(get_session),
):
    key = f"oauth_state:{state}"
    state_value = await request.app.state.redis.getdel(key)
    if not state_value:
        return Response(status_code=400, content="Invalid or expired state")
    decoded = state_value.decode() if isinstance(state_value, bytes) else state_value
    # Value is the cli_session_id when the login was initiated from the CLI,
    # or the sentinel "1" for a regular browser login.
    cli_session_id: str | None = decoded if decoded != "1" else None

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            token_resp = await client.post(
                _GITHUB_TOKEN_URL,
                data={
                    "client_id": settings.github_client_id,
                    "client_secret": settings.github_client_secret,
                    "code": code,
                },
                headers={"Accept": "application/json"},
            )
            token_resp.raise_for_status()
            access_token = token_resp.json().get("access_token")
            if not access_token:
                return Response(status_code=400, content="GitHub OAuth failed")

            user_resp = await client.get(
                _GITHUB_USER_URL,
                headers={"Authorization": f"Bearer {access_token}", "Accept": "application/vnd.github+json"},
            )
            user_resp.raise_for_status()
            gh_user = user_resp.json()
    except httpx.HTTPError:
        return Response(status_code=502, content="GitHub API unavailable")
    except ValueError:
        return Response(status_code=502, content="Invalid response from GitHub")

    github_id = gh_user.get("id")
    github_login_name = gh_user.get("login")
    if not github_id or not github_login_name:
        return Response(status_code=502, content="Incomplete GitHub user data")

    try:
        user, org, membership = await _upsert_user_org(session, github_id, github_login_name, gh_user)
    except IntegrityError as exc:
        await session.rollback()
        result = await session.execute(select(User).where(User.github_id == github_id))
        user = result.scalar_one_or_none()
        if user is None:
            # IntegrityError was not a same-user race (e.g. org slug collision) — surface it
            raise exc
        # Race: two simultaneous first-logins for the same GitHub user — continue as returning user
        result2 = await session.execute(select(UserOrg).where(UserOrg.user_id == user.id, UserOrg.role == "owner"))
        membership = result2.scalar_one()
        result3 = await session.execute(select(Org).where(Org.id == membership.org_id))
        org = result3.scalar_one()

    token = create_jwt(user_id=user.id, org_id=org.id, role=membership.role)
    if cli_session_id:
        await request.app.state.redis.set(f"cli_session:{cli_session_id}", token, ex=300)
        return Response(content=f'{{"token":"{token}"}}', media_type="application/json")
    # Browser login: pass token + one-time nonce via URL so Next.js can set its own cookie.
    # The nonce is consumed (GETDEL) by validate-nonce before cookies are written,
    # preventing cross-site requests from hijacking the session.
    # Fragment is never sent to servers or stored in Referer/access logs
    nonce = secrets.token_urlsafe(32)
    await request.app.state.redis.set(f"cookie_nonce:{nonce}", token, ex=_COOKIE_NONCE_TTL)
    return RedirectResponse(url=f"{settings.frontend_url}/auth/callback#token={token}&nonce={nonce}", status_code=302)


class ValidateNonceRequest(BaseModel):
    nonce: str
    token: str


@router.post("/validate-nonce")
async def validate_nonce(body: ValidateNonceRequest, request: Request):
    """One-time validation of a cookie-setting nonce.

    Called by the Next.js API route (/api/auth/set-token) before writing
    auth cookies.  The nonce is atomically deleted (GETDEL) so it can
    never be replayed.
    """
    key = f"cookie_nonce:{body.nonce}"
    stored = await request.app.state.redis.getdel(key)
    if not stored:
        return Response(status_code=400, content='{"error":"Invalid or expired nonce"}', media_type="application/json")
    stored_str = stored.decode() if isinstance(stored, bytes) else stored
    if stored_str != body.token:
        return Response(status_code=400, content='{"error":"Nonce/token mismatch"}', media_type="application/json")
    return {"ok": True}


@router.delete("/logout")
async def logout():
    response = Response(status_code=200)
    response.delete_cookie("argus_token")
    return response


async def _upsert_user_org(
    session: AsyncSession,
    github_id: int,
    github_login_name: str,
    gh_user: dict,
) -> tuple[User, Org, UserOrg]:
    """Upsert user + personal org + owner membership in a single transaction.

    All writes are flushed together and committed atomically. The caller is
    responsible for rolling back and retrying on IntegrityError (race condition).
    """
    result = await session.execute(select(User).where(User.github_id == github_id))
    existing_user = result.scalar_one_or_none()

    if existing_user is None:
        user = User(
            github_id=github_id,
            github_login=github_login_name,
            avatar_url=gh_user.get("avatar_url"),
        )
        session.add(user)
        await session.flush()
        org = Org(slug=github_login_name, name=gh_user.get("name") or github_login_name)
        session.add(org)
        await session.flush()
        membership = UserOrg(user_id=user.id, org_id=org.id, role="owner")
        session.add(membership)
        session.add(OrgBilling(org_id=org.id))
        await session.commit()
        return user, org, membership

    user = existing_user
    result2 = await session.execute(select(UserOrg).where(UserOrg.user_id == user.id, UserOrg.role == "owner"))
    membership = result2.scalar_one()
    result3 = await session.execute(select(Org).where(Org.id == membership.org_id))
    org = result3.scalar_one()
    return user, org, membership
