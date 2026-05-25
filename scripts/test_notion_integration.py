#!/usr/bin/env python
"""Manual test script for Notion OAuth flow + notification dispatch.

Commands:
  authorize  --org-id <id>           Print the URL to open in browser to connect Notion
  databases  --org-id <id>           List databases the bot can see (after OAuth)
  select-db  --org-id <id> --db <id> Save the chosen database ID to the integration
  fire       --org-id <id>           Send a fake review summary to the Notion database
  list       --org-id <id>           List Notion integrations for the org
  delete     --org-id <id> --id <id> Delete an integration row
"""

from __future__ import annotations

import asyncio
import sys

import httpx

GATEWAY = "http://localhost:8000"


def _get_token() -> str:
    import os

    token = os.getenv("ARGUS_TOKEN")
    if not token:
        print("Set ARGUS_TOKEN to a valid JWT, e.g.:")
        print("  export ARGUS_TOKEN=$(uv run python scripts/gen_token.py <org-id>)")
        sys.exit(1)
    return token


async def authorize(org_id: str) -> None:
    print("Open this URL in your browser to connect Notion:")
    print(f"  {GATEWAY}/api/v1/oauth/notion/authorize?org_id={org_id}")
    print()
    print("After authorizing, come back and run:")
    print(f"  uv run python scripts/test_notion_integration.py databases --org-id {org_id}")


async def databases(org_id: str) -> None:
    token = _get_token()
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{GATEWAY}/api/v1/orgs/{org_id}/integrations/notion/databases",
            headers={"Authorization": f"Bearer {token}"},
        )
    if resp.status_code != 200:
        print(f"Error {resp.status_code}: {resp.text}")
        sys.exit(1)
    dbs = resp.json()
    if not dbs:
        print("No databases found. Make sure the Notion bot has been added to at least one database.")
        return
    print(f"Found {len(dbs)} database(s):")
    for db in dbs:
        print(f"  {db['id']}  {db['title']}")
    print()
    print("Select one with:")
    print(f"  uv run python scripts/test_notion_integration.py select-db --org-id {org_id} --db <database-id>")


async def select_db(org_id: str, db_id: str) -> None:
    token = _get_token()
    async with httpx.AsyncClient() as client:
        resp = await client.patch(
            f"{GATEWAY}/api/v1/orgs/{org_id}/integrations/notion/database",
            headers={"Authorization": f"Bearer {token}"},
            json={"database_id": db_id},
        )
    if resp.status_code != 200:
        print(f"Error {resp.status_code}: {resp.text}")
        sys.exit(1)
    print(f"Database set: {db_id}")
    print()
    print("Now fire a test notification:")
    print(f"  uv run python scripts/test_notion_integration.py fire --org-id {org_id}")


async def fire(org_id: str) -> None:
    import os

    sys.path.insert(0, "packages/integrations")
    sys.path.insert(0, "packages/shared")

    os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://argus:argus@localhost:5432/argus")
    os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
    os.environ.setdefault("CELERY_BROKER_URL", "redis://localhost:6379/1")

    from integrations.notifications.dispatcher import dispatch_review_completed
    from integrations.notifications.schemas import ReviewSummary
    from shared.db import session_context

    summary = ReviewSummary(
        org_id=org_id,
        repo="acme/api",
        pr_number=99,
        pr_url="https://github.com/acme/api/pull/99",
        finding_count=5,
        critical_count=2,
        high_count=1,
    )

    async with session_context() as session:
        from shared.models.org_integration import OrgIntegration
        from sqlalchemy import select

        result = await session.execute(
            select(OrgIntegration).where(
                OrgIntegration.org_id == org_id,
                OrgIntegration.kind == "notion",
                OrgIntegration.enabled.is_(True),
            )
        )
        integrations = result.scalars().all()

    if not integrations:
        print("No Notion integration found. Run 'authorize' first.")
        sys.exit(1)

    cfg = integrations[0].config
    has_token = bool(cfg.get("token"))
    has_db = bool(cfg.get("database_id"))
    print(f"Found {len(integrations)} Notion integration(s).")
    print(f"  token present: {has_token}")
    print(f"  database_id:   {cfg.get('database_id', '(not set)')}")

    if not has_token or not has_db:
        print()
        print("Integration not fully configured. Run 'databases' then 'select-db' first.")
        sys.exit(1)

    print("Dispatching...")
    async with session_context() as session:
        await dispatch_review_completed(session, summary)
    print("Done. Check your Notion database for a new entry.")


async def list_integrations(org_id: str) -> None:
    token = _get_token()
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{GATEWAY}/api/v1/orgs/{org_id}/integrations",
            headers={"Authorization": f"Bearer {token}"},
        )
    if resp.status_code != 200:
        print(f"Error {resp.status_code}: {resp.text}")
        sys.exit(1)
    items = [i for i in resp.json() if i["kind"] == "notion"]
    if not items:
        print("No Notion integrations found.")
        return
    for i in items:
        print(f"id={i['id']}  enabled={i['enabled']}  config={i['config']}")


async def delete(org_id: str, integration_id: str) -> None:
    token = _get_token()
    async with httpx.AsyncClient() as client:
        resp = await client.delete(
            f"{GATEWAY}/api/v1/orgs/{org_id}/integrations/{integration_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
    if resp.status_code == 204:
        print(f"Deleted {integration_id}")
    else:
        print(f"Error {resp.status_code}: {resp.text}")
        sys.exit(1)


def usage() -> None:
    print(__doc__)
    sys.exit(1)


if __name__ == "__main__":
    args = sys.argv[1:]
    if not args:
        usage()

    cmd = args[0]
    kwargs: dict = {}
    i = 1
    while i < len(args):
        if args[i] == "--org-id" and i + 1 < len(args):
            kwargs["org_id"] = args[i + 1]
            i += 2
        elif args[i] == "--db" and i + 1 < len(args):
            kwargs["db_id"] = args[i + 1]
            i += 2
        elif args[i] == "--id" and i + 1 < len(args):
            kwargs["integration_id"] = args[i + 1]
            i += 2
        else:
            i += 1

    if cmd == "authorize":
        asyncio.run(authorize(**kwargs))
    elif cmd == "databases":
        asyncio.run(databases(**kwargs))
    elif cmd == "select-db":
        asyncio.run(select_db(**kwargs))
    elif cmd == "fire":
        asyncio.run(fire(**kwargs))
    elif cmd == "list":
        asyncio.run(list_integrations(**kwargs))
    elif cmd == "delete":
        asyncio.run(delete(**kwargs))
    else:
        usage()
