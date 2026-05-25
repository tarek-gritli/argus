from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from shared.db import session_context
from shared.models.org_integration import OrgIntegration
from sqlalchemy import select

router = APIRouter()

_SENSITIVE_KEYS = {"api_key", "webhook_url", "token", "access_token"}


def _get_org_id(request: Request) -> str:
    return request.state.org_id


def _mask_config(config: dict) -> dict:
    return {k: ("***" if k in _SENSITIVE_KEYS else v) for k, v in config.items()}


class IntegrationUpdate(BaseModel):
    enabled: bool


@router.get("/orgs/{org_id}/integrations")
async def list_integrations(org_id: str, org_id_from_token: str = Depends(_get_org_id)):
    if org_id_from_token != org_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    async with session_context() as session:
        result = await session.execute(select(OrgIntegration).where(OrgIntegration.org_id == org_id))
        items = result.scalars().all()
    return [
        {
            "id": i.id,
            "kind": i.kind,
            "enabled": i.enabled,
            "config": _mask_config(i.config),
            "created_at": i.created_at,
            "updated_at": i.updated_at,
        }
        for i in items
    ]


@router.patch("/orgs/{org_id}/integrations/{integration_id}")
async def update_integration(
    org_id: str,
    integration_id: str,
    body: IntegrationUpdate,
    org_id_from_token: str = Depends(_get_org_id),
):
    if org_id_from_token != org_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    async with session_context() as session:
        result = await session.execute(
            select(OrgIntegration).where(
                OrgIntegration.id == integration_id,
                OrgIntegration.org_id == org_id,
            )
        )
        integration = result.scalar_one_or_none()
        if not integration:
            raise HTTPException(status_code=404, detail="Integration not found")
        integration.enabled = body.enabled
        await session.commit()
    return {
        "id": integration.id,
        "kind": integration.kind,
        "enabled": integration.enabled,
        "config": _mask_config(integration.config),
    }


@router.delete("/orgs/{org_id}/integrations/{integration_id}", status_code=204)
async def delete_integration(
    org_id: str,
    integration_id: str,
    org_id_from_token: str = Depends(_get_org_id),
):
    if org_id_from_token != org_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    async with session_context() as session:
        result = await session.execute(
            select(OrgIntegration).where(
                OrgIntegration.id == integration_id,
                OrgIntegration.org_id == org_id,
            )
        )
        integration = result.scalar_one_or_none()
        if not integration:
            raise HTTPException(status_code=404, detail="Integration not found")
        await session.delete(integration)
        await session.commit()
