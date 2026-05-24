# apps/agents/specialized/ticket_compliance/validator.py
from __future__ import annotations

_CONFIDENCE_FLOOR = 0.6


def validate_findings(findings: list[dict]) -> list[dict]:
    """Drop findings below the confidence floor."""
    return [f for f in findings if float(f.get("confidence", 0)) >= _CONFIDENCE_FLOOR]
