from shared.models import Org, OrgBilling, User, UserOrg


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


def test_org_billing_defaults():
    billing = OrgBilling(org_id="org-1")
    assert billing.plan == "free"
    assert billing.reviews_used_this_month == 0


def test_free_plan_quota():
    billing = OrgBilling(org_id="a", plan="free")
    assert billing.monthly_limit == 50


def test_pro_plan_quota_per_seat():
    billing = OrgBilling(org_id="b", plan="pro", seat_count=5)
    assert billing.monthly_limit == 500  # 5 × 100


def test_team_plan_quota_per_seat():
    billing = OrgBilling(org_id="c", plan="team", seat_count=10)
    assert billing.monthly_limit == 1000  # 10 × 100
