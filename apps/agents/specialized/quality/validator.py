"""
Self-validation for quality agent findings.

Runs AFTER the LLM returns raw JSON, BEFORE converting to FindingSchema.
Drops or downgrades findings that fail sanity checks.
This is the agent's "self-reflection step" from the pipeline spec.
"""

from __future__ import annotations

import logging
from typing import Any

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
        confidence = float(finding.get("confidence", 0))
        if confidence < _MIN_CONFIDENCE:
            logger.debug("Dropping low-confidence finding: %s (%.2f)", finding["title"], confidence)
            continue

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
        valid_severities = {"critical", "high", "medium", "low", "info"}
        if finding["severity"] not in valid_severities:
            finding["severity"] = "medium"

        # --- Suggestion fallback ---
        if not finding.get("suggestion"):
            finding["suggestion"] = None

        # --- Fix fallback ---
        finding.setdefault("fix", None)

        valid.append(finding)

    # Sort by severity weight, then confidence
    _severity_weight = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}
    valid.sort(key=lambda f: (_severity_weight.get(f["severity"], 5), -float(f["confidence"])))

    if len(valid) > _MAX_FINDINGS:
        logger.info("Capping findings from %d to %d", len(valid), _MAX_FINDINGS)
        valid = valid[:_MAX_FINDINGS]

    return valid
