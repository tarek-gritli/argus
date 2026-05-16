"""
Auto-generate a structured PR description from the diff using Gemini.

Detects the PR type (Feature / Bug Fix / Hotfix / Improvement / Refactor)
and fills in the appropriate template, even if the developer wrote nothing.
"""

from __future__ import annotations

import json
import logging
import re

from .gemini_client import call_gemini

logger = logging.getLogger(__name__)

_TEMPLATES = {
    "feature": """\
## Feature

### Overview
{overview}

### Changes Made
- **Added:** {added}
- **Updated:** {updated}
- **Removed:** {removed}

### Implementation Details
{implementation_details}
""",
    "bug_fix": """\
## Bug Fix

### Issue Description
{issue_description}

### Root Cause
{root_cause}

### Fix Applied
- **Added:** {added}
- **Updated:** {updated}
- **Removed:** {removed}
""",
    "hotfix": """\
## Hotfix

### Urgency Level
- [ ] Critical (production down)
- [ ] High (major functionality broken)
- [ ] Medium (minor issue affecting users)

### Issue Summary
{issue_summary}

### Fix Applied
{fix_applied}
""",
    "improvement": """\
## Improvement

### Summary of Improvement
{summary}

### Key Improvements
- **Optimized:** {optimized}
- **Enhanced:** {enhanced}
- **Standardized:** {standardized}
""",
    "refactor": """\
## Refactor Summary

### What Was Refactored?
{what_refactored}

### Technical Details
- {technical_details}
""",
}

_SYSTEM_PROMPT = """\
You are a senior engineer writing pull request descriptions.
Analyze the diff and output a JSON object with exactly these fields:

{
  "pr_type": "feature" | "bug_fix" | "hotfix" | "improvement" | "refactor",
  "overview": "1-2 sentence summary of what this PR does",
  "issue_description": "describe the bug if bug_fix/hotfix",
  "root_cause": "root cause if bug_fix",
  "issue_summary": "summary if hotfix",
  "fix_applied": "what was done to fix it",
  "added": "comma-separated list of new things added",
  "updated": "comma-separated list of existing things changed",
  "removed": "N/A or comma-separated list of things removed",
  "implementation_details": "technical approach, architecture decisions",
  "summary": "improvement summary",
  "optimized": "what was optimized",
  "enhanced": "what was enhanced",
  "standardized": "what was standardized",
  "what_refactored": "what module/component was refactored",
  "technical_details": "new architecture, design patterns, risks"
}

Rules:
- Be concise and specific. Use actual names from the diff (function names, file names).
- If a field is not applicable, write "N/A".
- Output ONLY the JSON object, no prose, no markdown fences.
"""


def _has_meaningful_pr_body(body: str) -> bool:
    """Return True if the PR body contains substantial non-template content."""
    if not body or not isinstance(body, str):
        return False
    stripped = body.strip()
    cleaned = re.sub(r"(?m)^\s*[-*]\s*\[[ xX]\]\s*.*$", "", stripped)
    cleaned = re.sub(r"(?m)^\s{0,3}#{1,6}\s+.*$", "", cleaned)
    cleaned = re.sub(r"\b(N/?A|TBD|TODO)\b", "", cleaned, flags=re.IGNORECASE)
    return len(cleaned.strip()) > 120


def generate_pr_description(
    diff: str,
    pr_title: str,
    existing_body: str,
) -> str | None:
    """Analyze the diff and return a structured PR description string.

    Returns None if generation fails, so the caller can skip updating.
    """
    if existing_body and _has_meaningful_pr_body(existing_body):
        logger.info("PR already has a detailed description — skipping auto-generation.")
        return None

    prompt = f"PR Title: {pr_title}\n\nDiff:\n{diff[:60_000]}"
    raw = call_gemini(_SYSTEM_PROMPT, prompt, fallback="")
    if not raw:
        return None

    cleaned = re.sub(r"```(?:json)?\s*", "", raw).strip()
    start, end = cleaned.find("{"), cleaned.rfind("}")
    if start == -1 or end == -1:
        logger.warning("Could not parse PR description JSON from Gemini response")
        return None

    try:
        data = json.loads(cleaned[start : end + 1])
    except json.JSONDecodeError as exc:
        logger.warning("JSON decode error in PR description: %s", exc)
        return None

    pr_type = data.get("pr_type", "feature")
    template = _TEMPLATES.get(pr_type, _TEMPLATES["feature"])

    try:
        return template.format_map(_SafeDict(data))
    except Exception as exc:
        logger.warning("Template formatting failed: %s", exc)
        return None


class _SafeDict(dict):
    """Returns 'N/A' for missing keys instead of raising KeyError."""

    def __missing__(self, key: str) -> str:
        return "N/A"
