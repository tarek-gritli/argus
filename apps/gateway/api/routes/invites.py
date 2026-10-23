from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, HTTPException, Request
from integrations.email.client import invite_html, send_email
from pydantic import BaseModel, field_validator
from shared.config import get_settings
from shared.db import session_context
from shared.models import Org, OrgBilling, OrgInvite, User, UserOrg
from sqlalchemy import func, select

router = APIRouter()
logger = logging.getLogger(__name__)


def _check_org(request: Request, org_id: str) -> None:
    if request.state.org_id != org_id:
        raise HTTPException(status_code=403, detail="Forbidden")


def _check_owner(request: Request, action: str) -> None:
    if request.state.role != "owner":
        raise HTTPException(status_code=403, detail=f"Only owners can {action}")


# ── Members ──────────────────────────────────────────────────────────────────


@router.get("/orgs/{org_id}/members")
async def list_members(org_id: str, request: Request):
    _check_org(request, org_id)
    async with session_context() as session:
        rows = (await session.execute(select(UserOrg, User).join(User, UserOrg.user_id == User.id).where(UserOrg.org_id == org_id).order_by(UserOrg.joined_at))).all()
    return [
        {
            "user_id": uo.user_id,
            "github_login": u.login,
            "avatar_url": u.avatar_url,
            "role": uo.role,
            "joined_at": uo.joined_at.isoformat(),
        }
        for uo, u in rows
    ]


# ── Invite list + creation ────────────────────────────────────────────────────


class InviteRequest(BaseModel):
    email: str
    role: Literal["member"] = "member"

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        v = v.strip().lower()
        parts = v.split("@")
        if len(parts) != 2 or not parts[0] or "." not in parts[1]:
            raise ValueError("Invalid email address")
        return v


@router.get("/orgs/{org_id}/invites")
async def list_invites(org_id: str, request: Request):
    _check_org(request, org_id)
    async with session_context() as session:
        rows = (await session.execute(select(OrgInvite, User).join(User, OrgInvite.invited_by == User.id).where(OrgInvite.org_id == org_id, OrgInvite.accepted_at.is_(None)).order_by(OrgInvite.created_at.desc()))).all()
    return [
        {
            "id": inv.id,
            "email": inv.email,
            "role": inv.role,
            "invited_by_login": u.login,
            "expires_at": inv.expires_at.isoformat(),
            "created_at": inv.created_at.isoformat(),
        }
        for inv, u in rows
    ]


@router.post("/orgs/{org_id}/invites", status_code=201)
async def create_invite(org_id: str, body: InviteRequest, request: Request):
    _check_org(request, org_id)
    _check_owner(request, "invite members")

    settings = get_settings()

    async with session_context() as session:
        billing = (await session.execute(select(OrgBilling).where(OrgBilling.org_id == org_id))).scalar_one_or_none()
        if not billing or billing.plan == "free":
            raise HTTPException(status_code=403, detail="Upgrade to Pro to invite team members")

        members = await session.scalar(select(func.count()).where(UserOrg.org_id == org_id)) or 0
        pending = (
            await session.scalar(
                select(func.count()).where(
                    OrgInvite.org_id == org_id,
                    OrgInvite.accepted_at.is_(None),
                    OrgInvite.expires_at > datetime.now(timezone.utc),
                )
            )
            or 0
        )
        if members + pending >= billing.seat_count:
            raise HTTPException(
                status_code=403,
                detail="Seat limit reached. Upgrade your plan to add more seats.",
            )

        org = (await session.execute(select(Org).where(Org.id == org_id))).scalar_one()
        inviter = (await session.execute(select(User).where(User.id == request.state.user_id))).scalar_one()

        invite = OrgInvite(org_id=org_id, email=body.email, role=body.role, invited_by=inviter.id)
        session.add(invite)
        await session.commit()
        await session.refresh(invite)
        invite_id, invite_token, org_name, inviter_login = invite.id, invite.token, org.name, inviter.login

    if settings.resend_api_key:
        html = invite_html(org_name, inviter_login, f"{settings.frontend_url}/invite/{invite_token}")
        try:
            await send_email(
                settings.resend_api_key,
                body.email,
                f"You've been invited to {org_name} on Argus",
                html,
            )
        except Exception:
            logger.warning("Failed to send invite email to %s", body.email)

    return {"id": invite_id, "email": body.email}


@router.delete("/orgs/{org_id}/invites/{invite_id}", status_code=204)
async def revoke_invite(org_id: str, invite_id: str, request: Request):
    _check_org(request, org_id)
    _check_owner(request, "revoke invites")
    async with session_context() as session:
        invite = (await session.execute(select(OrgInvite).where(OrgInvite.id == invite_id, OrgInvite.org_id == org_id))).scalar_one_or_none()
        if not invite:
            raise HTTPException(status_code=404, detail="Invite not found")
        await session.delete(invite)
        await session.commit()


# ── Public invite info + accept ───────────────────────────────────────────────


@router.get("/invites/{token}")
async def get_invite(token: str):
    async with session_context() as session:
        row = (
            await session.execute(
                select(OrgInvite, Org, User)
                .join(Org, OrgInvite.org_id == Org.id)
                .join(User, OrgInvite.invited_by == User.id)
                .where(
                    OrgInvite.token == token,
                    OrgInvite.accepted_at.is_(None),
                    OrgInvite.expires_at > datetime.now(timezone.utc),
                )
            )
        ).first()
    if not row:
        raise HTTPException(status_code=404, detail="Invite not found or expired")
    invite, org, inviter = row
    return {
        "org_name": org.name,
        "org_id": org.id,
        "inviter_login": inviter.login,
        "role": invite.role,
        "email": invite.email,
        "expires_at": invite.expires_at.isoformat(),
    }
