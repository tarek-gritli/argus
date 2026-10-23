from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from api.routes.auth import _consume_invite
from api.routes.invites import InviteRequest
from pydantic import ValidationError
from shared.models.invite import OrgInvite


def test_invite_request_normalises_email():
    assert InviteRequest(email="  Bob@Example.COM ").email == "bob@example.com"


@pytest.mark.parametrize("bad", ["nope", "a@b", "a@@b.com"])
def test_invite_request_rejects_bad_email(bad):
    with pytest.raises(ValidationError):
        InviteRequest(email=bad)


def test_invite_request_rejects_owner_role():
    with pytest.raises(ValidationError):
        InviteRequest(email="a@b.com", role="owner")


def _session(*results):
    session = AsyncMock()
    session.add = MagicMock()
    session.execute = AsyncMock(side_effect=[MagicMock(scalar_one_or_none=MagicMock(return_value=r)) for r in results])
    return session


@pytest.mark.asyncio
async def test_consume_invite_unknown_token_returns_none():
    assert await _consume_invite(_session(None), "u1", "bad") is None


@pytest.mark.asyncio
async def test_consume_invite_adds_membership_and_marks_accepted():
    invite = OrgInvite(org_id="o1", email="a@b.com", invited_by="u0")
    session = _session(invite, None)

    assert await _consume_invite(session, "u1", invite.token) == ("o1", "member")

    assert invite.accepted_at is not None
    assert invite.accepted_at <= datetime.now(timezone.utc) + timedelta(seconds=1)
    session.add.assert_called_once()
    session.commit.assert_awaited_once()
