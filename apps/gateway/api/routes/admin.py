from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from shared.db import session_context
from shared.models import Org, OrgBilling
from sqlalchemy import select

router = APIRouter()

_VALID_PLANS = {"free", "pro", "team", "enterprise"}


def _get_org_id(request: Request) -> str:
    return request.state.org_id


class PlanUpdate(BaseModel):
    plan: str
    seat_count: int = Field(default=1, ge=1)


@router.post("/orgs/{org_id}/plan")
async def update_org_plan(org_id: str, body: PlanUpdate, user_org_id: str = Depends(_get_org_id)):
    if user_org_id != org_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    if body.plan not in _VALID_PLANS:
        raise HTTPException(status_code=400, detail=f"Invalid plan. Must be one of: {_VALID_PLANS}")
    async with session_context() as session:
        org_result = await session.execute(select(Org).where(Org.id == org_id))
        if not org_result.scalar_one_or_none():
            raise HTTPException(status_code=404, detail="Org not found")
        billing_result = await session.execute(select(OrgBilling).where(OrgBilling.org_id == org_id))
        billing = billing_result.scalar_one_or_none()
        seat_count = 1 if body.plan == "free" else body.seat_count
        if billing:
            billing.plan = body.plan
            billing.seat_count = seat_count
        else:
            billing = OrgBilling(org_id=org_id, plan=body.plan, seat_count=seat_count)
            session.add(billing)
        await session.commit()
    return {"org_id": org_id, "plan": billing.plan, "seat_count": billing.seat_count, "monthly_limit": billing.monthly_limit}
