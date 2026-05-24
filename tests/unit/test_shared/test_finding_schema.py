import pytest
from pydantic import ValidationError
from shared.schemas import FindingSchema, FixSchema

VALID_FINDING = {
    "agent": "security",
    "severity": "high",
    "file": "src/auth.py",
    "line_start": 10,
    "line_end": 20,
    "title": "SQL Injection",
    "description": "User input not sanitized.",
    "confidence": 0.9,
}


def test_finding_schema_valid():
    finding = FindingSchema(**VALID_FINDING)
    assert finding.agent == "security"
    assert finding.severity == "high"
    assert finding.suggestion is None
    assert finding.fix is None


def test_finding_schema_all_fields():
    finding = FindingSchema(
        **VALID_FINDING,
        suggestion="Use parameterized queries.",
        fix=FixSchema(diff="- raw\n+ safe", description="Sanitize input"),
    )
    assert finding.suggestion == "Use parameterized queries."
    assert finding.fix is not None
    assert finding.fix.diff == "- raw\n+ safe"


def test_finding_schema_invalid_severity():
    with pytest.raises(ValidationError):
        FindingSchema(**{**VALID_FINDING, "severity": "blocker"})


def test_finding_schema_invalid_agent():
    with pytest.raises(ValidationError):
        FindingSchema(**{**VALID_FINDING, "agent": "unknown_agent"})


def test_finding_schema_all_valid_severities():
    for severity in ["critical", "high", "medium", "low", "info"]:
        finding = FindingSchema(**{**VALID_FINDING, "severity": severity})
        assert finding.severity == severity


def test_finding_schema_all_valid_agents():
    for agent in [
        "security",
        "quality",
        "testing",
        "documentation",
        "ticket_compliance",
    ]:
        finding = FindingSchema(**{**VALID_FINDING, "agent": agent})
        assert finding.agent == agent


def test_finding_schema_missing_required_field():
    incomplete = {k: v for k, v in VALID_FINDING.items() if k != "title"}
    with pytest.raises(ValidationError):
        FindingSchema(**incomplete)


def test_fix_schema_all_optional():
    fix = FixSchema()
    assert fix.diff is None
    assert fix.description is None
