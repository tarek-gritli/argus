from datetime import datetime, timedelta, timezone


def test_org_invite_defaults():
    from shared.models.invite import OrgInvite

    invite = OrgInvite(org_id="org-1", email="user@example.com", invited_by="user-1")
    assert invite.role == "member"
    assert invite.accepted_at is None
    assert invite.token is not None
    assert len(invite.token) > 10
    now = datetime.now(timezone.utc)
    assert invite.expires_at > now + timedelta(days=6)
    assert invite.expires_at < now + timedelta(days=8)


def test_org_billing_has_billing_email():
    from shared.models.org_billing import OrgBilling

    b = OrgBilling(org_id="org-1")
    assert b.billing_email is None
