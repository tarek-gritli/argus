from shared.models import Org, User, UserOrg


def test_org_creation():
    org = Org(slug="acme", name="Acme Corp")
    assert org.slug == "acme"
    assert org.name == "Acme Corp"


def test_user_has_no_org_id():
    user = User(github_id=123, github_login="alice")
    assert not hasattr(user, "org_id")
    assert not hasattr(user, "role")


def test_user_org_role_explicit_member():
    uo = UserOrg(user_id="u1", org_id="o1", role="member")
    assert uo.role == "member"


def test_user_org_owner_role():
    uo = UserOrg(user_id="u1", org_id="o1", role="owner")
    assert uo.role == "owner"
