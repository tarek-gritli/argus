from __future__ import annotations

import re

from auth_utils import create_jwt
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, field_validator
from shared.db import get_session
from shared.models import Org, OrgBilling, UserOrg
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from .auth import issue_cookie_nonce, unique_org_slug

router = APIRouter()

# Every org gets its own free quota, so unbounded org creation would be unbounded free reviews.
MAX_OWNED_ORGS = 5


class OrgCreate(BaseModel):
    name: str

    @field_validator("name")
    @classmethod
    def _clean(cls, v: str) -> str:
        v = v.strip()
        if not 2 <= len(v) <= 60:
            raise ValueError("Name must be 2-60 characters")
        return v


def _org_json(org: Org, role: str, current_org_id: str) -> dict:
    return {"id": org.id, "name": org.name, "slug": org.slug, "role": role, "current": org.id == current_org_id}


@router.get("/orgs")
async def list_orgs(request: Request, session: AsyncSession = Depends(get_session)):
    rows = (await session.execute(select(UserOrg, Org).join(Org, UserOrg.org_id == Org.id).where(UserOrg.user_id == request.state.user_id).order_by(UserOrg.joined_at))).all()
    return [_org_json(org, uo.role, request.state.org_id) for uo, org in rows]


@router.post("/orgs", status_code=201)
async def create_org(body: OrgCreate, request: Request, session: AsyncSession = Depends(get_session)):
    user_id: str = request.state.user_id
    owned = await session.scalar(select(func.count()).where(UserOrg.user_id == user_id, UserOrg.role == "owner")) or 0
    if owned >= MAX_OWNED_ORGS:
        raise HTTPException(status_code=403, detail=f"You can own at most {MAX_OWNED_ORGS} organizations")

    base = re.sub(r"[^a-z0-9]+", "-", body.name.lower()).strip("-")
    org = Org(slug=await unique_org_slug(session, base), name=body.name)
    session.add(org)
    await session.flush()
    session.add(UserOrg(user_id=user_id, org_id=org.id, role="owner"))
    session.add(OrgBilling(org_id=org.id))
    await session.commit()
    return _org_json(org, "owner", request.state.org_id)


@router.post("/orgs/{org_id}/switch")
async def switch_org(org_id: str, request: Request, session: AsyncSession = Depends(get_session)):
    """Re-issue the session token scoped to another org the user belongs to."""
    membership = (await session.execute(select(UserOrg).where(UserOrg.user_id == request.state.user_id, UserOrg.org_id == org_id))).scalar_one_or_none()
    if membership is None:
        raise HTTPException(status_code=404, detail="Organization not found")
    token = create_jwt(user_id=request.state.user_id, org_id=org_id, role=membership.role)
    # The browser hands this to /api/auth/set-token, which requires a one-time nonce.
    return {"token": token, "nonce": await issue_cookie_nonce(request, token)}
