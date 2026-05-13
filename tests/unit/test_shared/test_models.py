from shared.models import Org


def test_org_creation():
    org = Org(slug="acme", name="Acme Corp")
    assert org.slug == "acme"
    assert org.name == "Acme Corp"
