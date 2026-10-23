from __future__ import annotations

import json
import logging
import re
import secrets
from datetime import datetime, timezone
from typing import Literal

import httpx
from auth_utils import create_jwt
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import RedirectResponse
from identity_providers import IdentityProvider, Profile, ProviderError, get_providers
from pydantic import BaseModel
from shared.config import Settings, get_settings
from shared.db import get_session
from shared.models import AuthIdentity, Org, OrgBilling, OrgInvite, User, UserOrg
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()
logger = logging.getLogger(__name__)

ProviderName = Literal["github", "gitlab"]

_CSRF_TTL = 600  # 10 minutes
_COOKIE_NONCE_TTL = 300  # 5 minutes
_LINK_COOKIE = "argus_link_state"


def _provider_or_404(name: str, settings: Settings) -> IdentityProvider:
    provider = get_providers(settings).get(name)
    if provider is None:
        raise HTTPException(status_code=404, detail="Sign-in provider not available")
    return provider


async def _store_state(request: Request, **fields: str) -> str:
    state = secrets.token_urlsafe(32)
    value = json.dumps({k: v or "" for k, v in fields.items()})
    await request.app.state.redis.set(f"oauth_state:{state}", value, ex=_CSRF_TTL)
    return state


async def issue_cookie_nonce(request: Request, token: str) -> str:
    """One-time nonce that lets Next.js's /api/auth/set-token write cookies for `token`."""
    nonce = secrets.token_urlsafe(32)
    await request.app.state.redis.set(f"cookie_nonce:{nonce}", token, ex=_COOKIE_NONCE_TTL)
    return nonce


@router.get("/providers")
async def list_providers(settings: Settings = Depends(get_settings)):
    """Sign-in methods the login page and Settings can offer."""
    return [{"id": p.name, "label": p.label, "host": p.host} for p in get_providers(settings).values()]


@router.get("/{provider}/login")
async def login(
    provider: ProviderName,
    request: Request,
    cli_session_id: str | None = None,
    invite_token: str | None = None,
    settings: Settings = Depends(get_settings),
):
    p = _provider_or_404(provider, settings)
    # cli_session_id / invite_token ride along in server-side state: providers don't
    # round-trip unknown query params back to the callback.
    state = await _store_state(request, cli=cli_session_id or "", invite=invite_token or "")
    return RedirectResponse(url=p.authorize_url(state))


@router.get("/link/{provider}")
async def link(provider: ProviderName, request: Request, settings: Settings = Depends(get_settings)):
    """Start connecting another sign-in method to the signed-in user (authenticated route)."""
    p = _provider_or_404(provider, settings)
    state = await _store_state(request, link=request.state.user_id)
    response = RedirectResponse(url=p.authorize_url(state))
    # Binds this flow to this browser, so a link URL can't be replayed in a victim's browser
    # to attach their provider account to the attacker's Argus account.
    response.set_cookie(_LINK_COOKIE, state, max_age=_CSRF_TTL, httponly=True, samesite="lax", secure=settings.env != "development")
    return response


@router.get("/{provider}/callback")
async def callback(
    provider: ProviderName,
    code: str,
    state: str,
    request: Request,
    settings: Settings = Depends(get_settings),
    session: AsyncSession = Depends(get_session),
):
    p = _provider_or_404(provider, settings)
    state_value = await request.app.state.redis.getdel(f"oauth_state:{state}")
    if not state_value:
        return Response(status_code=400, content="Invalid or expired state")
    decoded = state_value.decode() if isinstance(state_value, bytes) else state_value
    try:
        state_obj = json.loads(decoded)
        cli_session_id: str | None = state_obj.get("cli") or None
        invite_token: str | None = state_obj.get("invite") or None
        link_user_id: str | None = state_obj.get("link") or None
    except (json.JSONDecodeError, ValueError, AttributeError):
        # Legacy format: raw cli_session_id, or the sentinel "1" for a browser login.
        cli_session_id = decoded if decoded != "1" else None
        invite_token = link_user_id = None

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            profile = await p.fetch_profile(client, code)
    except ProviderError as exc:
        return Response(status_code=exc.status, content=str(exc))
    except httpx.HTTPError:
        return Response(status_code=502, content=f"{p.label} API unavailable")
    except ValueError:
        return Response(status_code=502, content=f"Invalid response from {p.label}")

    if link_user_id:
        return await _finish_link(request, session, settings, p, profile, link_user_id, state)

    try:
        user, org, membership = await _login_or_signup(session, p, profile)
    except IntegrityError as exc:
        await session.rollback()
        # Two simultaneous first sign-ins for the same account: the other request won, use its user.
        identity = await _find_identity(session, p, profile.provider_user_id)
        if identity is None:
            raise exc  # not that race (e.g. a slug collision) — surface it
        user, org, membership = await _personal_org(session, identity.user_id)

    token_org_id, token_role = org.id, membership.role
    if invite_token:
        accepted = await _consume_invite(session, user.id, invite_token, set(profile.verified_emails))
        if accepted:
            token_org_id, token_role = accepted

    token = create_jwt(user_id=user.id, org_id=token_org_id, role=token_role)
    if cli_session_id:
        await request.app.state.redis.set(f"cli_session:{cli_session_id}", token, ex=300)
        return Response(content=f'{{"token":"{token}"}}', media_type="application/json")
    # Browser login: pass token + one-time nonce via URL so Next.js can set its own cookie.
    # The nonce is consumed (GETDEL) by validate-nonce before cookies are written,
    # preventing cross-site requests from hijacking the session.
    # Fragment is never sent to servers or stored in Referer/access logs
    nonce = await issue_cookie_nonce(request, token)
    return RedirectResponse(url=f"{settings.frontend_url}/auth/callback#token={token}&nonce={nonce}", status_code=302)


async def _finish_link(
    request: Request,
    session: AsyncSession,
    settings: Settings,
    provider: IdentityProvider,
    profile: Profile,
    user_id: str,
    state: str,
) -> Response:
    outcome = "state"
    if request.cookies.get(_LINK_COOKIE) == state:
        outcome = await _link_identity(session, user_id, provider, profile)
    key = "linked" if outcome == "ok" else "link_error"
    value = provider.name if outcome == "ok" else outcome
    response = RedirectResponse(url=f"{settings.frontend_url}/dashboard/settings?{key}={value}", status_code=302)
    response.delete_cookie(_LINK_COOKIE)
    return response


async def _find_identity(session: AsyncSession, provider: IdentityProvider, subject: str) -> AuthIdentity | None:
    return (
        await session.execute(
            select(AuthIdentity).where(
                AuthIdentity.provider == provider.name,
                AuthIdentity.provider_host == provider.host,
                AuthIdentity.provider_user_id == subject,
            )
        )
    ).scalar_one_or_none()


async def _link_identity(session: AsyncSession, user_id: str, provider: IdentityProvider, profile: Profile) -> str:
    """Attach the provider account to `user_id`. Returns "ok" or an error code for the UI."""
    existing = await _find_identity(session, provider, profile.provider_user_id)
    if existing is not None:
        return "ok" if existing.user_id == user_id else "already_linked"
    has_one = await session.scalar(
        select(func.count()).where(
            AuthIdentity.user_id == user_id,
            AuthIdentity.provider == provider.name,
            AuthIdentity.provider_host == provider.host,
        )
    )
    if has_one:
        return "provider_taken"  # already has a different account from this provider
    try:
        session.add(_new_identity(user_id, provider, profile))
        await session.commit()
    except IntegrityError:
        await session.rollback()
        return "already_linked"
    return "ok"


def _new_identity(user_id: str, provider: IdentityProvider, profile: Profile) -> AuthIdentity:
    return AuthIdentity(
        user_id=user_id,
        provider=provider.name,
        provider_host=provider.host,
        provider_user_id=profile.provider_user_id,
        login=profile.login,
        email=profile.primary_email,
        avatar_url=profile.avatar_url,
    )


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


# ── Connected sign-in methods ────────────────────────────────────────────────


@router.get("/identities")
async def list_identities(request: Request, session: AsyncSession = Depends(get_session)):
    rows = (await session.execute(select(AuthIdentity).where(AuthIdentity.user_id == request.state.user_id).order_by(AuthIdentity.created_at))).scalars().all()
    return [
        {
            "id": i.id,
            "provider": i.provider,
            "host": i.provider_host,
            "login": i.login,
            "email": i.email,
            "avatar_url": i.avatar_url,
            "linked_at": i.created_at.isoformat(),
        }
        for i in rows
    ]


@router.delete("/identities/{identity_id}", status_code=204)
async def unlink_identity(identity_id: str, request: Request, session: AsyncSession = Depends(get_session)):
    mine = (await session.execute(select(AuthIdentity).where(AuthIdentity.user_id == request.state.user_id))).scalars().all()
    target = next((i for i in mine if i.id == identity_id), None)
    if target is None:
        raise HTTPException(status_code=404, detail="Identity not found")
    if len(mine) == 1:
        raise HTTPException(status_code=400, detail="Cannot remove your only sign-in method")
    await session.delete(target)
    await session.commit()


# ── Account creation ─────────────────────────────────────────────────────────


async def _personal_org(session: AsyncSession, user_id: str) -> tuple[User, Org, UserOrg]:
    """The user's first owned org (their personal one — created at sign-up)."""
    user = (await session.execute(select(User).where(User.id == user_id))).scalar_one()
    membership = (await session.execute(select(UserOrg).where(UserOrg.user_id == user_id, UserOrg.role == "owner").order_by(UserOrg.joined_at).limit(1))).scalar_one()
    org = (await session.execute(select(Org).where(Org.id == membership.org_id))).scalar_one()
    return user, org, membership


async def unique_org_slug(session: AsyncSession, base: str, suffix_hint: str = "") -> str:
    """`base` if free, else `base-<hint>`, else with a random suffix. Unique-index races still raise."""
    base = re.sub(r"[^A-Za-z0-9._-]+", "-", base).strip("-") or "org"
    candidates = [base] + ([f"{base}-{suffix_hint}"] if suffix_hint else [])
    for slug in candidates:
        if await session.scalar(select(Org.id).where(Org.slug == slug)) is None:
            return slug
    while True:
        slug = f"{base}-{secrets.token_hex(3)}"
        if await session.scalar(select(Org.id).where(Org.slug == slug)) is None:
            return slug


async def _login_or_signup(session: AsyncSession, provider: IdentityProvider, profile: Profile) -> tuple[User, Org, UserOrg]:
    """Resolve the identity to a user, creating user + personal org + owner membership on first sight.

    All writes commit together. The caller rolls back and retries on IntegrityError (race).
    """
    identity = await _find_identity(session, provider, profile.provider_user_id)
    if identity is not None:
        # Keep the cached profile fresh (logins and avatars change at the provider)
        identity.login, identity.avatar_url = profile.login, profile.avatar_url
        identity.email = profile.primary_email or identity.email
        await session.commit()
        return await _personal_org(session, identity.user_id)

    user = User(login=profile.login, avatar_url=profile.avatar_url)
    session.add(user)
    await session.flush()
    session.add(_new_identity(user.id, provider, profile))
    org = Org(slug=await unique_org_slug(session, profile.login, provider.name), name=profile.name or profile.login)
    session.add(org)
    await session.flush()
    membership = UserOrg(user_id=user.id, org_id=org.id, role="owner")
    session.add(membership)
    session.add(OrgBilling(org_id=org.id))
    await session.commit()
    return user, org, membership


async def _consume_invite(session: AsyncSession, user_id: str, token: str, verified_emails: set[str]) -> tuple[str, str] | None:
    """Accept a pending invite: create the membership and mark the invite accepted.

    Returns (org_id, role) on success. Returns None if the token is unknown, used or
    expired, if none of the user's verified emails match the invited address, or if the
    org has no free seat.
    """
    result = await session.execute(
        select(OrgInvite).where(
            OrgInvite.token == token,
            OrgInvite.accepted_at.is_(None),
            OrgInvite.expires_at > datetime.now(timezone.utc),
        )
    )
    invite = result.scalar_one_or_none()
    if not invite or invite.email.lower() not in verified_emails:
        return None

    existing = await session.execute(select(UserOrg).where(UserOrg.user_id == user_id, UserOrg.org_id == invite.org_id))
    if not existing.scalar_one_or_none():
        seats = await session.scalar(select(OrgBilling.seat_count).where(OrgBilling.org_id == invite.org_id))
        members = await session.scalar(select(func.count()).where(UserOrg.org_id == invite.org_id)) or 0
        if seats is None or members >= seats:
            return None
        session.add(UserOrg(user_id=user_id, org_id=invite.org_id, role=invite.role))

    invite.accepted_at = datetime.now(timezone.utc)
    await session.commit()
    return invite.org_id, invite.role
