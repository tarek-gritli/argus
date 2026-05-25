from unittest.mock import AsyncMock, MagicMock

import pytest


@pytest.mark.asyncio
async def test_get_or_create_org_existing_repo():
    """If repo already exists, return its org_id without creating anything."""
    from org_resolver import get_or_create_org

    mock_repo = MagicMock()
    mock_repo.org_id = "existing-org-id"

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_repo

    mock_session = AsyncMock()
    mock_session.execute = AsyncMock(return_value=mock_result)

    org_id = await get_or_create_org(mock_session, installation_id=999, repo_full_name="owner/repo")

    assert org_id == "existing-org-id"
    mock_session.add.assert_not_called()


@pytest.mark.asyncio
async def test_get_or_create_org_new_installation():
    """If repo not found, create Org + Repo and return new org_id."""
    from org_resolver import get_or_create_org
    from shared.models import Org, Repo

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None

    added_objects = []

    mock_session = AsyncMock()
    mock_session.execute = AsyncMock(return_value=mock_result)
    mock_session.add = MagicMock(side_effect=added_objects.append)
    mock_session.flush = AsyncMock()
    mock_session.commit = AsyncMock()

    org_id = await get_or_create_org(mock_session, installation_id=42, repo_full_name="acme/service")

    assert mock_session.flush.called
    assert mock_session.commit.called
    assert len(added_objects) == 3
    org_obj = added_objects[0]
    repo_obj = added_objects[1]
    billing_obj = added_objects[2]
    assert isinstance(org_obj, Org)
    assert isinstance(repo_obj, Repo)
    from shared.models.org_billing import OrgBilling

    assert isinstance(billing_obj, OrgBilling)
    assert billing_obj.org_id == org_obj.id
    assert repo_obj.installation_id == 42
    assert repo_obj.full_name == "acme/service"
    assert repo_obj.org_id == org_obj.id
    assert org_id == org_obj.id


@pytest.mark.asyncio
async def test_get_or_create_org_existing_installation_new_repo():
    """Org slug conflict on flush → recover by attaching a new Repo to the existing Org.
    OrgBilling is created when it doesn't exist yet on the recovered org."""
    from org_resolver import get_or_create_org
    from shared.models import Repo
    from shared.models.org_billing import OrgBilling
    from sqlalchemy.exc import IntegrityError

    existing_org_id = "existing-org-id"

    mock_existing_org = MagicMock()
    mock_existing_org.id = existing_org_id

    # execute call sequence after IntegrityError path:
    #   1. initial repo lookup         → None (repo not found)
    #   2. repo re-query post-rollback → None (still not found)
    #   3. org lookup by slug          → existing org
    #   4. billing lookup              → None (not yet created)
    no_result = MagicMock()
    no_result.scalar_one_or_none.return_value = None
    existing_org_result = MagicMock()
    existing_org_result.scalar_one_or_none.return_value = mock_existing_org

    added_objects = []

    mock_session = AsyncMock()
    mock_session.execute = AsyncMock(side_effect=[no_result, no_result, existing_org_result, no_result])
    mock_session.add = MagicMock(side_effect=added_objects.append)
    mock_session.flush = AsyncMock(side_effect=IntegrityError("slug", {}, Exception()))
    mock_session.rollback = AsyncMock()
    mock_session.commit = AsyncMock()

    result_org_id = await get_or_create_org(mock_session, installation_id=42, repo_full_name="acme/new-service")

    assert mock_session.rollback.called
    assert mock_session.commit.called
    # Org added before flush + Repo + OrgBilling added in recovery
    assert len(added_objects) == 3
    repo_obj = added_objects[1]
    billing_obj = added_objects[2]
    assert isinstance(repo_obj, Repo)
    assert isinstance(billing_obj, OrgBilling)
    assert repo_obj.installation_id == 42
    assert repo_obj.full_name == "acme/new-service"
    assert repo_obj.org_id == existing_org_id
    assert billing_obj.org_id == existing_org_id
    assert result_org_id == existing_org_id


@pytest.mark.asyncio
async def test_get_or_create_org_existing_installation_new_repo_billing_exists():
    """Org slug conflict on flush → billing row already exists, so OrgBilling is NOT added again."""
    from org_resolver import get_or_create_org
    from shared.models import Repo
    from shared.models.org_billing import OrgBilling
    from sqlalchemy.exc import IntegrityError

    existing_org_id = "existing-org-id"

    mock_existing_org = MagicMock()
    mock_existing_org.id = existing_org_id

    mock_existing_billing = MagicMock(spec=OrgBilling)

    no_result = MagicMock()
    no_result.scalar_one_or_none.return_value = None
    existing_org_result = MagicMock()
    existing_org_result.scalar_one_or_none.return_value = mock_existing_org
    existing_billing_result = MagicMock()
    existing_billing_result.scalar_one_or_none.return_value = mock_existing_billing

    added_objects = []

    mock_session = AsyncMock()
    mock_session.execute = AsyncMock(side_effect=[no_result, no_result, existing_org_result, existing_billing_result])
    mock_session.add = MagicMock(side_effect=added_objects.append)
    mock_session.flush = AsyncMock(side_effect=IntegrityError("slug", {}, Exception()))
    mock_session.rollback = AsyncMock()
    mock_session.commit = AsyncMock()

    result_org_id = await get_or_create_org(mock_session, installation_id=42, repo_full_name="acme/new-service")

    assert result_org_id == existing_org_id
    # Org + Repo only — no duplicate OrgBilling
    assert len(added_objects) == 2
    assert isinstance(added_objects[1], Repo)
