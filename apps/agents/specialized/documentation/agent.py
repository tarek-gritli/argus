"""
Documentation agent — LangGraph node.

Pipeline:
  1. Input          — receive AgentInput
  2. Static checks  — missing docstrings, stale comments, param coverage, README gaps
  3. LLM analysis   — Claude reviews diff for nuanced documentation issues
  4. Merge & dedupe — combine static + LLM findings, drop duplicates
  5. Validate       — filter low-confidence, enforce limits
  6. Output         — list[FindingSchema]

Design principle:
  Static checks are fast, zero-cost, and high-precision for structural issues
  (missing docstrings, bare TODOs). Claude handles the qualitative assessment
  (stale comments, README completeness, misleading descriptions).
  The two passes are union-merged so neither alone is a single point of failure.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from google import genai
from shared.config import get_settings
from shared.schemas.finding import FindingSchema

from .checks.missing_docstrings import run_missing_docstring_checks
from .checks.param_coverage import run_param_coverage_checks
from .checks.readme_gaps import run_readme_gap_checks
from .checks.stale_comments import run_stale_comment_checks
from .prompts.system import DOCUMENTATION_SYSTEM_PROMPT
from .schemas import AgentInput
from .validator import validate_findings

logger = logging.getLogger(__name__)

# Gemini 2.0 Flash — free tier, 1M token context window
_MODEL = "gemini-2.0-flash"


# ---------------------------------------------------------------------------
# Static analysis pass
# ---------------------------------------------------------------------------


def _run_static_checks(input: AgentInput) -> list[dict[str, Any]]:
    context = {
        "diff": input.diff,
        "changed_files": input.changed_files,
    }
    findings: list[dict[str, Any]] = []
    findings.extend(run_missing_docstring_checks(context))
    findings.extend(run_stale_comment_checks(context))
    findings.extend(run_param_coverage_checks(context))
    findings.extend(run_readme_gap_checks(context))
    return findings


# ---------------------------------------------------------------------------
# Prompt assembly
# ---------------------------------------------------------------------------


def _build_user_prompt(input: AgentInput, static_summary: str) -> str:
    sections = [
        "## PR Context",
        f"Repository: {input.repo_full_name}",
        f"PR #{input.pr_number}: {input.pr_title}",
    ]

    if input.pr_description:
        sections.append(f"Description: {input.pr_description[:500]}")

    sections += [
        "",
        "## Static Analysis Pre-scan",
        "The following structural issues were already detected by static checks.",
        "Do NOT repeat them. Focus on qualitative issues the static scan cannot catch:",
        "misleading descriptions, wrong terminology, outdated explanations, README completeness.",
        "",
        static_summary or "None detected.",
        "",
        "## Diff",
        "```diff",
        input.diff[:40_000],
        "```",
        "",
        "Review the diff for documentation issues not covered by the static scan above.",
        "Output ONLY a JSON array of findings. Return [] if there are no additional issues.",
    ]

    return "\n".join(sections)


def _summarize_static(findings: list[dict[str, Any]]) -> str:
    if not findings:
        return ""
    lines = []
    for f in findings:
        lines.append(f"- [{f['severity'].upper()}] {f['file']}:{f['line_start']} — {f['title']}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# LLM call
# ---------------------------------------------------------------------------


def _call_gemini(system: str, user: str) -> str:
    settings = get_settings()
    if not settings.gemini_api_key:
        raise RuntimeError("GEMINI_API_KEY is not set in environment")
    client = genai.Client(api_key=settings.gemini_api_key)
    response = client.models.generate_content(
        model=_MODEL,
        contents=f"{system}\n\n{user}",
    )
    return response.text or ""


# ---------------------------------------------------------------------------
# Response parsing
# ---------------------------------------------------------------------------


def _parse_findings(raw: str) -> list[dict[str, Any]]:
    cleaned = re.sub(r"```(?:json)?\s*", "", raw).strip()
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
# Deduplication
# ---------------------------------------------------------------------------


def _dedup(findings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Drop findings that refer to the same file+line+title (case-insensitive)."""
    seen: set[tuple[str, int, str]] = set()
    result = []
    for f in findings:
        key = (f.get("file", ""), int(f.get("line_start", 0)), f.get("title", "").lower()[:40])
        if key not in seen:
            seen.add(key)
            result.append(f)
    return result


# ---------------------------------------------------------------------------
# FindingSchema conversion
# ---------------------------------------------------------------------------


def _to_finding_schemas(findings: list[dict[str, Any]]) -> list[FindingSchema]:
    schemas = []
    for f in findings:
        try:
            schemas.append(FindingSchema(**f))
        except Exception as exc:  # noqa: BLE001
            logger.warning("Could not convert to FindingSchema: %s", exc)
    return schemas


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def run_documentation_agent(input: AgentInput) -> list[FindingSchema]:
    logger.info(
        "Documentation agent starting: %s PR#%d head=%s",
        input.repo_full_name,
        input.pr_number,
        input.head_sha[:8],
    )

    # Step 2: Static checks (fast, no LLM)
    static_findings = _run_static_checks(input)
    logger.info("Static checks returned %d findings", len(static_findings))

    # Step 3: LLM analysis — focus on what static can't catch
    static_summary = _summarize_static(static_findings)
    user_prompt = _build_user_prompt(input, static_summary)

    logger.info("Calling Gemini for documentation review...")
    raw_response = _call_gemini(DOCUMENTATION_SYSTEM_PROMPT, user_prompt)
    logger.debug("Raw LLM response length: %d chars", len(raw_response))

    llm_findings = _parse_findings(raw_response)
    logger.info("LLM returned %d findings", len(llm_findings))

    # Step 4: Merge static + LLM, deduplicate
    combined = static_findings + llm_findings
    combined = _dedup(combined)
    logger.info("After dedup: %d combined findings", len(combined))

    # Step 5: Validate
    validated = validate_findings(combined)
    logger.info("After validation: %d findings", len(validated))

    # Step 6: Convert to FindingSchema
    return _to_finding_schemas(validated)
