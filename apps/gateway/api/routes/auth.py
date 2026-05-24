from __future__ import annotations

import secrets

import httpx
from auth_utils import create_jwt
from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import RedirectResponse
from shared.config import Settings, get_settings
from shared.db import get_session
from shared.models import Org, User, UserOrg
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()

_GITHUB_AUTHORIZE_URL = "https://github.com/login/oauth/authorize"
_GITHUB_TOKEN_URL = "https://github.com/login/oauth/access_token"
_GITHUB_USER_URL = "https://api.github.com/user"
_CSRF_TTL = 600  # 10 minutes


@router.get("/github/login")
async def github_login(request: Request, settings: Settings = Depends(get_settings)):
    state = secrets.token_urlsafe(32)
    await request.app.state.redis.set(f"oauth_state:{state}", "1", ex=_CSRF_TTL)
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
    valid = await request.app.state.redis.getdel(key)
    if not valid:
        return Response(status_code=400, content="Invalid or expired state")

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
    response = Response(content=f'{{"token":"{token}"}}', media_type="application/json")
    response.set_cookie(
        "argus_token",
        token,
        httponly=True,
        samesite="lax",
        secure=settings.env != "development",
    )
    return response


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
        await session.commit()
        return user, org, membership

    user = existing_user
    result2 = await session.execute(select(UserOrg).where(UserOrg.user_id == user.id, UserOrg.role == "owner"))
    membership = result2.scalar_one()
    result3 = await session.execute(select(Org).where(Org.id == membership.org_id))
    org = result3.scalar_one()
    return user, org, membership
