from __future__ import annotations

import asyncio
import secrets

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from gitlab.exceptions import GitlabError
from integrations.gitlab import DEFAULT_BASE_URL, InvalidGitLabURL, get_gitlab_client, normalize_base_url
from permissions import require_owner
from pydantic import BaseModel
from shared.config import get_settings
from shared.crypto import decrypt, encrypt
from shared.db import session_context
from shared.models.org_integration import OrgIntegration
from sqlalchemy import select

router = APIRouter()

_SENSITIVE_KEYS = {"api_key", "webhook_url", "token", "access_token", "webhook_secret", "signing_token"}
_NOTION_API = "https://api.notion.com/v1"
_NOTION_VERSION = "2022-06-28"

# Which config keys must be present for an integration to be considered ready.
_READY_KEYS: dict[str, set[str]] = {
    "slack": {"webhook_url"},
    "notion": {"token", "database_id"},
    "linear": {"access_token"},
    "jira": {"access_token", "cloud_id"},
    "gitlab": {"base_url", "access_token", "webhook_secret"},
}


def _get_org_id(request: Request) -> str:
    return request.state.org_id


def _mask_config(config: dict) -> dict:
    return {k: ("***" if k in _SENSITIVE_KEYS else v) for k, v in config.items()}


def _webhook_url(integration_id: str) -> str:
    return f"{get_settings().app_base_url}/api/v1/webhooks/gitlab/{integration_id}"


def _is_ready(kind: str, config: dict) -> bool:
    required = _READY_KEYS.get(kind, set())
    return all(config.get(k) for k in required)


class GitLabConnect(BaseModel):
    base_url: str = DEFAULT_BASE_URL  # gitlab.com or a self-hosted instance
    access_token: str
    signing_token: str | None = None  # optional GitLab webhook signing token (whsec_...)


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
            "ready": _is_ready(i.kind, i.config),
            "config": _mask_config(i.config),
            **({"webhook_url": _webhook_url(i.id)} if i.kind == "gitlab" else {}),
            "created_at": i.created_at,
            "updated_at": i.updated_at,
        }
        for i in items
    ]


@router.patch("/orgs/{org_id}/integrations/{integration_id}", dependencies=[Depends(require_owner)])
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
        "ready": _is_ready(integration.kind, integration.config),
        "config": _mask_config(integration.config),
    }


@router.delete("/orgs/{org_id}/integrations/{integration_id}", status_code=204, dependencies=[Depends(require_owner)])
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


@router.get("/orgs/{org_id}/integrations/{integration_id}/notion/databases", dependencies=[Depends(require_owner)])
async def list_notion_databases(
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
                OrgIntegration.kind == "notion",
            )
        )
        integration = result.scalar_one_or_none()
    if not integration:
        raise HTTPException(status_code=404, detail="Notion integration not found")
    raw_token = integration.config.get("token", "")
    if not raw_token:
        raise HTTPException(status_code=400, detail="Notion token missing")
    try:
        token = decrypt(raw_token)
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Invalid Notion token configuration") from exc
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
    return [{"id": db["id"], "title": db.get("title", [{}])[0].get("plain_text", "(untitled)")} for db in data.get("results", [])]


@router.patch("/orgs/{org_id}/integrations/{integration_id}/notion/database", dependencies=[Depends(require_owner)])
async def select_notion_database(
    org_id: str,
    integration_id: str,
    body: NotionDatabaseSelect,
    org_id_from_token: str = Depends(_get_org_id),
):
    if org_id_from_token != org_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    async with session_context() as session:
        result = await session.execute(
            select(OrgIntegration).where(
                OrgIntegration.id == integration_id,
                OrgIntegration.org_id == org_id,
                OrgIntegration.kind == "notion",
            )
        )
        integration = result.scalar_one_or_none()
        if not integration:
            raise HTTPException(status_code=404, detail="Notion integration not found")
        integration.config = {**integration.config, "database_id": body.database_id}
        await session.commit()
    return {"status": "ok", "database_id": body.database_id}


def _verify_gitlab_token(base_url: str, token: str) -> None:
    """Blocking: resolve the host (SSRF guard) and confirm the token authenticates."""
    gl = get_gitlab_client(base_url, token)
    gl.auth()


@router.post("/orgs/{org_id}/integrations/gitlab", status_code=201, dependencies=[Depends(require_owner)])
async def connect_gitlab(
    org_id: str,
    body: GitLabConnect,
    org_id_from_token: str = Depends(_get_org_id),
):
    """Connect a GitLab instance. The webhook secret is returned once — paste it into GitLab."""
    if org_id_from_token != org_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    try:
        await asyncio.to_thread(_verify_gitlab_token, body.base_url, body.access_token)
    except InvalidGitLabURL as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except GitlabError as exc:
        raise HTTPException(status_code=400, detail="GitLab rejected the access token") from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail="Could not reach the GitLab instance") from exc

    secret = secrets.token_urlsafe(32)
    config = {
        "base_url": normalize_base_url(body.base_url),
        "access_token": encrypt(body.access_token),
        "webhook_secret": encrypt(secret),
    }
    if body.signing_token:
        config["signing_token"] = encrypt(body.signing_token)
    async with session_context() as session:
        integration = OrgIntegration(org_id=org_id, kind="gitlab", config=config)
        session.add(integration)
        await session.commit()
        integration_id = integration.id
    return {"id": integration_id, "webhook_url": _webhook_url(integration_id), "webhook_secret": secret}


@router.post("/orgs/{org_id}/integrations/{integration_id}/gitlab/rotate-secret", dependencies=[Depends(require_owner)])
async def rotate_gitlab_secret(
    org_id: str,
    integration_id: str,
    org_id_from_token: str = Depends(_get_org_id),
):
    if org_id_from_token != org_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    secret = secrets.token_urlsafe(32)
    async with session_context() as session:
        integration = (
            await session.execute(
                select(OrgIntegration).where(
                    OrgIntegration.id == integration_id,
                    OrgIntegration.org_id == org_id,
                    OrgIntegration.kind == "gitlab",
                )
            )
        ).scalar_one_or_none()
        if not integration:
            raise HTTPException(status_code=404, detail="GitLab integration not found")
        integration.config = {**integration.config, "webhook_secret": encrypt(secret)}
        await session.commit()
    return {"webhook_url": _webhook_url(integration_id), "webhook_secret": secret}
