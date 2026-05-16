from __future__ import annotations

from shared.models import Org, Repo
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession


async def get_or_create_org(session: AsyncSession, installation_id: int, repo_full_name: str) -> str:
    """Return org_id for the (installation_id, repo_full_name) pair, creating Org+Repo if first seen."""
    result = await session.execute(select(Repo).where(Repo.installation_id == installation_id, Repo.full_name == repo_full_name))
    repo = result.scalar_one_or_none()
    if repo:
        return repo.org_id

    try:
        org = Org(slug=f"install-{installation_id}", name=f"install-{installation_id}")
        session.add(org)
        await session.flush()
        repo = Repo(org_id=org.id, full_name=repo_full_name, installation_id=installation_id)
        session.add(repo)
        await session.commit()
        return org.id
    except IntegrityError:
        await session.rollback()
        # Re-query the repo first — the common race where both Org+Repo were created concurrently.
        result = await session.execute(select(Repo).where(Repo.installation_id == installation_id, Repo.full_name == repo_full_name))
        repo = result.scalar_one_or_none()
        if repo:
            return repo.org_id
        # Org slug conflict: another request created the Org but not this Repo yet.
        org_slug = f"install-{installation_id}"
        org_result = await session.execute(select(Org).where(Org.slug == org_slug))
        org = org_result.scalar_one_or_none()
        if org is None:
            raise
        try:
            session.add(Repo(org_id=org.id, full_name=repo_full_name, installation_id=installation_id))
            await session.commit()
            return org.id
        except IntegrityError:
            await session.rollback()
            result = await session.execute(select(Repo).where(Repo.installation_id == installation_id, Repo.full_name == repo_full_name))
            repo = result.scalar_one_or_none()
            if repo:
                return repo.org_id
            raise
