from shared.models import Org


def test_org_defaults():
    org = Org(slug="acme", name="Acme Corp")
    assert org.plan == "free"
    assert org.review_quota == 50
    assert org.reviews_used_this_month == 0


def test_plan_quota_mapping():
    free_org = Org(slug="a", name="A", plan="free")
    pro_org = Org(slug="b", name="B", plan="pro")
    team_org = Org(slug="c", name="C", plan="team")
    assert free_org.review_quota == 50
    assert pro_org.review_quota == 500
    assert team_org.review_quota == -1
