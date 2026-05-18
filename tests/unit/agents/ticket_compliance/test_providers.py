# tests/unit/agents/ticket_compliance/test_providers.py
from specialized.ticket_compliance.providers.base import TicketData
from specialized.ticket_compliance.schemas import AgentInput


def test_ticket_data_fields():
    td = TicketData(
        id="42",
        title="Add rate limiting to the API",
        description="We need per-org rate limiting on the gateway.",
        url="https://github.com/org/repo/issues/42",
    )
    assert td.id == "42"
    assert td.title == "Add rate limiting to the API"


def test_agent_input_defaults():
    inp = AgentInput(
        diff="",
        repo_full_name="org/repo",
        pr_number=1,
        head_sha="abc",
        base_sha="def",
        installation_id=0,
    )
    assert inp.pr_title == ""
    assert inp.pr_description == ""
