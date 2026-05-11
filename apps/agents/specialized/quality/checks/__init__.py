"""Check modules used by the quality agent."""

from __future__ import annotations

from typing import Any

from ..tools.ast_analyzer import StaticAnalysisResult
from ..tools.grep_patterns import PatternScanResult
from .complexity import run_complexity_checks
from .confidence import blend_scores, score_from_count, score_from_threshold
from .dead_code import run_dead_code_checks
from .duplication import run_duplication_checks
from .structure import run_structure_checks

FindingSchema = dict[str, Any]


def run_all_checks(
    static_result: StaticAnalysisResult,
    pattern_result: PatternScanResult,
) -> list[FindingSchema]:
    """Execute all deterministic checks and return candidate findings."""
    context = {
        "static_result": static_result,
        "pattern_result": pattern_result,
    }

    findings: list[FindingSchema] = []
    for check in (
        run_complexity_checks,
        run_duplication_checks,
        run_dead_code_checks,
        run_structure_checks,
    ):
        findings.extend(check(context))

    return findings


def to_prompt_context(findings: list[FindingSchema], max_items: int = 25) -> str:
    """Render deterministic check findings as a compact prompt section."""
    if not findings:
        return "=== Deterministic Checks: no candidate findings ==="

    lines = ["=== Deterministic Check Candidates ==="]
    for finding in findings[:max_items]:
        lines.append(f"  {finding.get('file')}:{finding.get('line_start')} [{finding.get('severity')}] {finding.get('title')}")

    if len(findings) > max_items:
        lines.append(f"  ... and {len(findings) - max_items} more")

    return "\n".join(lines)


__all__ = [
    "run_complexity_checks",
    "run_duplication_checks",
    "run_dead_code_checks",
    "run_structure_checks",
    "run_all_checks",
    "to_prompt_context",
    "score_from_threshold",
    "score_from_count",
    "blend_scores",
]
