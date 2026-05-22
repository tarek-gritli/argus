"""
Quality agent — invoked as a LangGraph node by the orchestrator.

Pipeline (matches AGENTS.md spec exactly):
  1. Input          — receive AgentInput
  2. Context inject — static analysis metrics (Phase 5: vector embeddings skipped)
  3. LLM analysis   — Claude reviews diff + metrics via structured prompt
  4. Self-validate  — filter false positives, enforce confidence floor
  5. Output         — list[FindingSchema]
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

import anthropic
from shared.config import get_settings
from shared.schemas.finding import FindingSchema

from .checks import run_all_checks
from .checks import to_prompt_context as checks_to_prompt_context
from .prompts.system import QUALITY_SYSTEM_PROMPT
from .schemas import AgentInput
from .tools.ast_analyzer import run_static_analysis
from .tools.grep_patterns import scan_diff_patterns
from .validator import validate_findings

logger = logging.getLogger(__name__)

_MODEL = "claude-haiku-4-5"
_MAX_TOKENS = 4096


# ---------------------------------------------------------------------------
# Prompt assembly
# ---------------------------------------------------------------------------


def _build_user_prompt(
    input: AgentInput,
    static_context: str,
    pattern_context: str,
    checks_context: str,
) -> str:
    sections = [
        "## PR Context",
        f"Repository: {input.repo_full_name}",
        f"PR #{input.pr_number}: {input.pr_title}",
    ]

    if input.pr_description:
        sections.append(f"Description: {input.pr_description[:500]}")

    if input.vector_context:
        sections += ["", "## Codebase Context (semantically similar code from this repo)"]
        for chunk in input.vector_context[:5]:
            sections += ["```", chunk[:2000], "```"]

    sections += [
        "",
        static_context,
        "",
        pattern_context,
        "",
        checks_context,
        "",
        "## Diff",
        "```diff",
        input.diff[:40_000],  # hard cap — avoid context overflow
        "```",
        "",
        "The deterministic candidates are hints only.",
        "Validate each candidate against the actual changed code before reporting it.",
        "",
        "Review the diff above for code quality issues. Output ONLY a JSON array of findings.",
        "If there are no meaningful quality issues, return an empty array: []",
    ]

    return "\n".join(sections)


# ---------------------------------------------------------------------------
# LLM call
# ---------------------------------------------------------------------------


def _call_claude(system: str, user: str) -> str:
    settings = get_settings()
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    message = client.messages.create(
        model=_MODEL,
        max_tokens=_MAX_TOKENS,
        system=system,
        messages=[{"role": "user", "content": user}],
    )

    for block in message.content:
        text = getattr(block, "text", None)
        if text:
            return text

    raise ValueError("Claude response did not include any text content")


# ---------------------------------------------------------------------------
# Response parsing
# ---------------------------------------------------------------------------


def _parse_findings(raw: str) -> list[dict[str, Any]]:
    """Extract JSON array from Claude's response, tolerating markdown fences."""
    # Strip markdown code fences if present
    cleaned = re.sub(r"```(?:json)?\s*", "", raw).strip()

    # Find the outermost JSON array
    start = cleaned.find("[")
    end = cleaned.rfind("]")
    if start == -1 or end == -1:
        logger.warning("No JSON array found in LLM response")
        return []

    try:
        return json.loads(cleaned[start : end + 1])
    except json.JSONDecodeError as exc:
        logger.error("Failed to parse findings JSON: %s", exc)
        return []


# ---------------------------------------------------------------------------
# FindingSchema conversion
# Note: imports from packages/shared at call time to avoid circular imports
# in dev/test environments where shared may not be installed.
# ---------------------------------------------------------------------------


def _to_finding_schemas(validated: list[dict[str, Any]]) -> list[FindingSchema]:
    schemas = []
    for f in validated:
        try:
            schemas.append(FindingSchema(**f))
        except Exception as exc:  # noqa: BLE001
            logger.warning("Could not convert finding to FindingSchema: %s", exc)
    return schemas


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def run_quality_agent(input: AgentInput) -> list[FindingSchema]:
    """
    Run the quality agent on a PR diff.

    Args:
        input: AgentInput with diff, file sources, and PR metadata.

    Returns:
        list[FindingSchema] — empty list if no issues found.
    """
    logger.info(
        "Quality agent starting: %s PR#%d head=%s",
        input.repo_full_name,
        input.pr_number,
        input.head_sha[:8],
    )

    # Step 2: Static analysis (context injection)
    static_result = run_static_analysis(input.changed_files)
    static_context = static_result.to_prompt_context()
    logger.debug("Static analysis complete: %d files", len(static_result.files))

    # Pattern scan across all files in the diff
    pattern_hits_all = []
    for file_path in input.changed_files:
        # Extract per-file diff slice (rough — good enough for pattern scan)
        file_diff_slice = _extract_file_diff(input.diff, file_path)
        scan = scan_diff_patterns(file_diff_slice, file_path)
        pattern_hits_all.extend(scan.hits)

    from .tools.grep_patterns import PatternScanResult

    combined_patterns = PatternScanResult(hits=pattern_hits_all)
    pattern_context = combined_patterns.to_prompt_context()
    deterministic_candidates = run_all_checks(static_result, combined_patterns)
    checks_context = checks_to_prompt_context(deterministic_candidates)

    # Step 3: LLM analysis
    system_prompt = QUALITY_SYSTEM_PROMPT
    user_prompt = _build_user_prompt(input, static_context, pattern_context, checks_context)

    logger.info("Calling Claude for quality review...")
    raw_response = _call_claude(system_prompt, user_prompt)
    logger.debug("Raw LLM response length: %d chars", len(raw_response))

    # Step 4: Parse + self-validate
    raw_findings = _parse_findings(raw_response)
    logger.info("LLM returned %d raw findings", len(raw_findings))

    validated = validate_findings(raw_findings)
    logger.info("After validation: %d findings", len(validated))

    # Step 5: Convert to FindingSchema
    return _to_finding_schemas(validated)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _extract_file_diff(full_diff: str, file_path: str) -> str:
    """
    Extract the diff section for a single file from the full PR diff.
    Returns empty string if not found.
    """
    lines = full_diff.splitlines(keepends=True)
    result: list[str] = []
    in_file = False

    for line in lines:
        if line.startswith("diff --git"):
            if in_file:
                break  # reached the next file — stop
            if file_path in line:
                in_file = True
                result = [line]
        elif in_file:
            result.append(line)

    return "".join(result)
