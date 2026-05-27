"""
Self-validation for quality agent findings.

Runs AFTER the LLM returns raw JSON, BEFORE converting to FindingSchema.
Drops or downgrades findings that fail sanity checks.
This is the agent's "self-reflection step" from the pipeline spec.
"""

from __future__ import annotations

import logging
from typing import Any

from ..confidence import (
    coerce_confidence,
    confidence_at_or_above,
    normalize_severity,
    sort_by_severity_then_confidence,
)

logger = logging.getLogger(__name__)

# Confidence below this → drop the finding entirely
_MIN_CONFIDENCE = 0.5

# Titles that suggest the LLM is echoing static metrics rather than adding insight
_SHALLOW_TITLE_PATTERNS = [
    "complexity score",
    "cyclomatic complexity is",
    "nesting depth is",
    "line count is",
    "magic number detected",
]

# Maximum findings to return — forces the agent to prioritize
_MAX_FINDINGS = 15


def validate_findings(raw_findings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Filter and clean raw LLM findings.

    Args:
        raw_findings: list of dicts parsed from Claude's JSON response.

    Returns:
        Cleaned list ready to be converted to FindingSchema.
    """
    valid: list[dict[str, Any]] = []

    for finding in raw_findings:
        # --- Required field check ---
        required = {
            "agent",
            "severity",
            "file",
            "line_start",
            "line_end",
            "title",
            "description",
            "confidence",
        }
        if not required.issubset(finding.keys()):
            missing = required - finding.keys()
            logger.warning("Dropping finding missing fields: %s", missing)
            continue

        # --- Force agent field ---
        finding["agent"] = "quality"

        # --- Confidence floor ---
        confidence = coerce_confidence(finding.get("confidence"))
        if confidence is None:
            logger.warning("Dropping finding with non-numeric confidence")
            continue
        if not confidence_at_or_above(confidence, _MIN_CONFIDENCE):
            logger.debug("Dropping low-confidence finding: %s (%.2f)", finding["title"], confidence)
            continue
        finding["confidence"] = confidence

        # --- Line range sanity ---
        line_start = finding.get("line_start", 0)
        line_end = finding.get("line_end", 0)
        if line_start <= 0 or line_end < line_start:
            logger.warning("Dropping finding with invalid line range: %s-%s", line_start, line_end)
            continue

        # --- Shallow finding detection ---
        title_lower = finding["title"].lower()
        if any(pattern in title_lower for pattern in _SHALLOW_TITLE_PATTERNS):
            logger.debug(
                "Dropping shallow finding that echoes static metrics: %s",
                finding["title"],
            )
            continue

        # --- Severity normalization ---
        finding["severity"] = normalize_severity(finding.get("severity"), default="medium")

        # --- Suggestion fallback ---
        if not finding.get("suggestion"):
            finding["suggestion"] = None

        # --- Fix fallback ---
        finding.setdefault("fix", None)

        valid.append(finding)

    # Sort by severity weight, then confidence
    sort_by_severity_then_confidence(valid)

    if len(valid) > _MAX_FINDINGS:
        logger.info("Capping findings from %d to %d", len(valid), _MAX_FINDINGS)
        valid = valid[:_MAX_FINDINGS]

    return valid
