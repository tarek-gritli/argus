# tests/unit/agents/ticket_compliance/test_agent.py
from specialized.ticket_compliance.validator import validate_findings


def test_validate_drops_low_confidence():
    findings = [
        {"agent": "ticket_compliance", "severity": "high", "file": "a.py", "line_start": 1, "line_end": 1, "title": "Missing feature", "description": "x", "suggestion": "add it", "confidence": 0.85},
        {"agent": "ticket_compliance", "severity": "medium", "file": "b.py", "line_start": 1, "line_end": 1, "title": "Partial impl", "description": "y", "suggestion": "fix it", "confidence": 0.3},
    ]
    result = validate_findings(findings)
    assert len(result) == 1
    assert result[0]["title"] == "Missing feature"


def test_validate_keeps_empty_list():
    assert validate_findings([]) == []


def test_validate_keeps_exactly_at_floor():
    findings = [
        {"agent": "ticket_compliance", "severity": "low", "file": "a.py", "line_start": 1, "line_end": 1, "title": "Minor gap", "description": "z", "suggestion": "fix it", "confidence": 0.6},
    ]
    result = validate_findings(findings)
    assert len(result) == 1
