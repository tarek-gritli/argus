from __future__ import annotations

from shared.models import Org, Repo
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


async def get_or_create_org(session: AsyncSession, installation_id: int, repo_full_name: str) -> str:
    """Return org_id for installation_id, creating Org+Repo if first seen."""
    result = await session.execute(select(Repo).where(Repo.installation_id == installation_id))
    repo = result.scalar_one_or_none()
    if repo:
        return repo.org_id

    org = Org(slug=f"install-{installation_id}", name=f"install-{installation_id}")
    session.add(org)
    await session.flush()
    repo = Repo(org_id=org.id, full_name=repo_full_name, installation_id=installation_id)
    session.add(repo)
    await session.commit()
    return org.id
