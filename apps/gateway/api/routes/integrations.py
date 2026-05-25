from __future__ import annotations

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from shared.crypto import decrypt
from shared.db import session_context
from shared.models.org_integration import OrgIntegration
from sqlalchemy import select

router = APIRouter()

_SENSITIVE_KEYS = {"api_key", "webhook_url", "token", "access_token"}
_NOTION_API = "https://api.notion.com/v1"
_NOTION_VERSION = "2022-06-28"


def _get_org_id(request: Request) -> str:
    return request.state.org_id


def _mask_config(config: dict) -> dict:
    return {k: ("***" if k in _SENSITIVE_KEYS else v) for k, v in config.items()}


class IntegrationUpdate(BaseModel):
    enabled: bool


class NotionDatabaseSelect(BaseModel):
    database_id: str


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


@router.get("/orgs/{org_id}/integrations/notion/databases")
async def list_notion_databases(org_id: str, org_id_from_token: str = Depends(_get_org_id)):
    if org_id_from_token != org_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    async with session_context() as session:
        result = await session.execute(
            select(OrgIntegration).where(
                OrgIntegration.org_id == org_id,
                OrgIntegration.kind == "notion",
                OrgIntegration.enabled.is_(True),
            )
        )
        integration = result.scalars().first()
    if not integration:
        raise HTTPException(status_code=404, detail="Notion integration not connected")
    token = decrypt(integration.config.get("token", ""))
    if not token:
        raise HTTPException(status_code=400, detail="Notion token missing")
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{_NOTION_API}/search",
                headers={"Authorization": f"Bearer {token}", "Notion-Version": _NOTION_VERSION},
                json={"filter": {"value": "database", "property": "object"}, "page_size": 100},
                timeout=10,
            )
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPStatusError as exc:
        raise HTTPException(status_code=502, detail="Notion API error") from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail="Failed to reach Notion") from exc
    databases = [{"id": db["id"], "title": db.get("title", [{}])[0].get("plain_text", "(untitled)")} for db in data.get("results", [])]
    return databases


@router.patch("/orgs/{org_id}/integrations/notion/database")
async def select_notion_database(
    org_id: str,
    body: NotionDatabaseSelect,
    org_id_from_token: str = Depends(_get_org_id),
):
    if org_id_from_token != org_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    async with session_context() as session:
        result = await session.execute(
            select(OrgIntegration).where(
                OrgIntegration.org_id == org_id,
                OrgIntegration.kind == "notion",
                OrgIntegration.enabled.is_(True),
            )
        )
        integration = result.scalars().first()
        if not integration:
            raise HTTPException(status_code=404, detail="Notion integration not connected")
        integration.config = {**integration.config, "database_id": body.database_id}
        await session.commit()
    return {"status": "ok", "database_id": body.database_id}
