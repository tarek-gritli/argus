"""Post-LLM validation for documentation agent findings."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

_MIN_CONFIDENCE = 0.55
_MAX_FINDINGS = 15

_VALID_SEVERITIES = {"critical", "high", "medium", "low", "info"}
_SEVERITY_WEIGHT = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}

# The documentation agent must never claim issues for things it cannot see
_SPECULATIVE_PATTERNS = [
    "no documentation exists",
    "entire codebase",
    "all functions",
    "project-wide",
    "everywhere",
]


def validate_findings(raw_findings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Filter, normalize, and rank documentation findings from the LLM."""
    valid: list[dict[str, Any]] = []
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

    for finding in raw_findings:
        if not isinstance(finding, dict):
            logger.warning("Dropping non-dict finding: %r", finding)
            continue

        if not required.issubset(finding.keys()):
            missing = required - finding.keys()
            logger.warning("Dropping finding missing fields: %s", missing)
            continue

        finding["agent"] = "documentation"

        if finding["severity"] not in _VALID_SEVERITIES:
            finding["severity"] = "medium"

        try:
            line_start = int(finding.get("line_start", 0))
            line_end = int(finding.get("line_end", 0))
        except (TypeError, ValueError):
            logger.warning("Dropping finding with non-integer line range")
            continue

        if line_start <= 0 or line_end < line_start:
            logger.warning("Dropping finding with invalid line range: %d-%d", line_start, line_end)
            continue

        try:
            confidence = float(finding.get("confidence", 0))
        except (TypeError, ValueError):
            logger.warning("Dropping finding with non-numeric confidence")
            continue

        title_lower = str(finding["title"]).lower()
        desc_lower = str(finding.get("description", "")).lower()
        for pattern in _SPECULATIVE_PATTERNS:
            if pattern in title_lower or pattern in desc_lower:
                confidence *= 0.5
                logger.debug("Penalizing speculative finding: %s", finding["title"])
                break

        finding["confidence"] = round(confidence, 3)

        if confidence < _MIN_CONFIDENCE:
            logger.debug("Dropping low-confidence finding: %s (%.2f)", finding["title"], confidence)
            continue

        suggestion = finding.get("suggestion", "").strip()
        if not suggestion:
            logger.debug("Dropping finding with no suggestion: %s", finding["title"])
            continue

        finding.setdefault("fix", None)
        valid.append(finding)

    valid.sort(key=lambda f: (_SEVERITY_WEIGHT.get(f["severity"], 5), -float(f["confidence"])))

    if len(valid) > _MAX_FINDINGS:
        logger.info("Capping findings from %d to %d", len(valid), _MAX_FINDINGS)
        valid = valid[:_MAX_FINDINGS]

    return valid
