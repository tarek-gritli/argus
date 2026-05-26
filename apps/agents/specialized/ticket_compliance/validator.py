# apps/agents/specialized/ticket_compliance/validator.py
from __future__ import annotations

from ..confidence import (
    coerce_confidence,
    confidence_at_or_above,
    normalize_severity,
    sort_by_severity_then_confidence,
)

_CONFIDENCE_FLOOR = 0.6


def validate_findings(findings: list[dict]) -> list[dict]:
    """Drop findings below confidence floor and normalize confidence/severity."""
    valid: list[dict] = []
    for finding in findings:
        confidence = coerce_confidence(finding.get("confidence"))
        if confidence is None:
            continue
        if not confidence_at_or_above(confidence, _CONFIDENCE_FLOOR):
            continue
        finding["confidence"] = confidence
        finding["severity"] = normalize_severity(finding.get("severity"), default="medium")
        valid.append(finding)

    sort_by_severity_then_confidence(valid)
    return valid
