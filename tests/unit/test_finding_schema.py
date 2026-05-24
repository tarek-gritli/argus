from shared.schemas.finding import FindingSchema


def test_ticket_compliance_agent_type_accepted():
    f = FindingSchema(
        agent="ticket_compliance",
        severity="medium",
        file="src/main.py",
        line_start=1,
        line_end=1,
        title="Ticket scope mismatch",
        description="PR does not implement what the issue describes.",
        confidence=0.8,
    )
    assert f.agent == "ticket_compliance"
