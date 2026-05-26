"""Validation and confidence policy for the security agent."""

from __future__ import annotations

import logging
from typing import Iterable

from ..confidence import confidence_at_or_above
from .schemas import Finding, ReflectionAction, ReflectionDecision, Severity

logger = logging.getLogger(__name__)

_MIN_CONFIDENCE = 0.60
_CRITICAL_DOWNGRADE_CONFIDENCE = 0.85
_SEVERITY_WEIGHT = {
    Severity.CRITICAL: 0,
    Severity.HIGH: 1,
    Severity.MEDIUM: 2,
    Severity.LOW: 3,
    Severity.INFO: 4,
}


def build_fallback_decisions(raw_findings: list[Finding]) -> list[ReflectionDecision]:
    """Apply the security confidence policy when reflection LLM is unavailable."""
    decisions: list[ReflectionDecision] = []

    for index, finding in enumerate(raw_findings):
        if not confidence_at_or_above(finding.confidence, _MIN_CONFIDENCE):
            decisions.append(
                ReflectionDecision(
                    finding_index=index,
                    action=ReflectionAction.DROP,
                    reason="Confidence below threshold.",
                )
            )
            continue

        if finding.severity == Severity.CRITICAL and not confidence_at_or_above(
            finding.confidence,
            _CRITICAL_DOWNGRADE_CONFIDENCE,
        ):
            decisions.append(
                ReflectionDecision(
                    finding_index=index,
                    action=ReflectionAction.DOWNGRADE,
                    reason="Critical severity unsupported by confidence.",
                    revised_severity=Severity.HIGH,
                )
            )
            continue

        decisions.append(
            ReflectionDecision(
                finding_index=index,
                action=ReflectionAction.KEEP,
                reason="Exploit path and confidence are acceptable.",
            )
        )

    return decisions


def validate_findings(findings: Iterable[Finding]) -> list[Finding]:
    """Apply the final security confidence policy to reflected findings."""
    valid: list[Finding] = []

    for finding in findings:
        confidence = finding.confidence
        if not confidence_at_or_above(confidence, _MIN_CONFIDENCE):
            logger.debug("Dropping low-confidence finding: %s (%.2f)", finding.message, confidence)
            continue

        if finding.severity == Severity.CRITICAL and not confidence_at_or_above(
            confidence,
            _CRITICAL_DOWNGRADE_CONFIDENCE,
        ):
            finding.severity = Severity.HIGH

        valid.append(finding)

    valid.sort(key=lambda item: (_SEVERITY_WEIGHT.get(item.severity, 5), -item.confidence))
    return valid
