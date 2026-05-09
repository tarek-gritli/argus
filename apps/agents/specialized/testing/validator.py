"""
Self-validation for testing agent findings.

Runs AFTER the LLM returns raw JSON, BEFORE converting to FindingSchema.

The testing agent has a specific failure mode: it hallucinates missing tests
that actually exist elsewhere in the test suite (outside the diff).
The validator applies a confidence penalty for findings that claim "no test exists"
unless the diff clearly shows new code with zero corresponding test additions.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

_MIN_CONFIDENCE = 0.5
_MAX_FINDINGS = 12

# Titles suggesting the agent is guessing about tests outside the diff
_SPECULATIVE_PATTERNS = [
    "no tests exist",
    "untested module",
    "no test suite",
    "test file missing",
    "no test coverage",  # too broad — agent can't know full coverage from diff
]

# Titles suggesting useful, specific findings
_STRONG_PATTERNS = [
    "no test",
    "missing test",
    "weak assertion",
    "always passes",
    "no assertion",
    "missing edge case",
    "untested",
    "missing error",
    "flaky",
]

_VALID_SEVERITIES = {"critical", "high", "medium", "low", "info"}
_SEVERITY_WEIGHT = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}


def validate_findings(
    raw_findings: list[dict[str, Any]],
    has_test_files_in_diff: bool = False,
) -> list[dict[str, Any]]:
    """
    Filter and clean raw LLM findings.

    Args:
        raw_findings:           List of dicts parsed from Claude's JSON response.
        has_test_files_in_diff: True if any test file was modified in this PR.
                                Used to apply confidence penalties on speculative findings.

    Returns:
        Cleaned list ready for FindingSchema conversion.
    """
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

        # Required fields
        if not required.issubset(finding.keys()):
            missing = required - finding.keys()
            logger.warning("Dropping finding missing fields: %s", missing)
            continue

        # Force correct agent tag
        finding["agent"] = "testing"

        # Severity normalization
        if finding["severity"] not in _VALID_SEVERITIES:
            finding["severity"] = "medium"

        # Line range sanity — coerce to int to handle string values from LLM
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

        # Penalize speculative "no tests anywhere" claims when test files WERE touched
        # (The agent might be right, but confidence should be lower)
        title_lower = finding["title"].lower()
        desc_lower = finding.get("description", "").lower()

        if has_test_files_in_diff:
            for pattern in _speculative_patterns_list():
                if pattern in title_lower or pattern in desc_lower:
                    confidence *= 0.6
                    logger.debug(
                        "Penalizing speculative finding (test files exist in diff): %s",
                        finding["title"],
                    )
                    break

        finding["confidence"] = round(confidence, 3)

        if confidence < _MIN_CONFIDENCE:
            logger.debug("Dropping low-confidence finding: %s (%.2f)", finding["title"], confidence)
            continue

        # Require suggestion to be non-empty (testing agent must always say what to add)
        suggestion = finding.get("suggestion", "").strip()
        if not suggestion:
            logger.debug("Dropping finding with no suggestion: %s", finding["title"])
            continue

        finding.setdefault("fix", None)

        valid.append(finding)

    # Sort: severity first, then confidence descending
    valid.sort(key=lambda f: (_SEVERITY_WEIGHT.get(f["severity"], 5), -float(f["confidence"])))

    if len(valid) > _MAX_FINDINGS:
        logger.info("Capping findings from %d to %d", len(valid), _MAX_FINDINGS)
        valid = valid[:_MAX_FINDINGS]

    return valid


def _speculative_patterns_list() -> list[str]:
    return _SPECULATIVE_PATTERNS
