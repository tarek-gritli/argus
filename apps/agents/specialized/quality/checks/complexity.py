"""Complexity checks: cyclomatic complexity and deep nesting."""

from __future__ import annotations

from typing import Any

from ...confidence import blend_scores, score_from_threshold
from ..tools.ast_analyzer import StaticAnalysisResult

FindingSchema = dict[str, Any]


_HIGH_COMPLEXITY_THRESHOLD = 10
_HIGH_NESTING_THRESHOLD = 4


def _make_finding(
    *,
    file_path: str,
    line_start: int,
    line_end: int,
    severity: str,
    title: str,
    description: str,
    suggestion: str,
    confidence: float,
) -> FindingSchema:
    return {
        "agent": "quality",
        "severity": severity,
        "file": file_path,
        "line_start": line_start,
        "line_end": line_end,
        "title": title,
        "description": description,
        "suggestion": suggestion,
        "confidence": confidence,
        "fix": None,
    }


def run_complexity_checks(context: dict[str, Any]) -> list[FindingSchema]:
    static_result = context.get("static_result")
    if not isinstance(static_result, StaticAnalysisResult):
        return []

    findings: list[FindingSchema] = []

    for file_metrics in static_result.files:
        if file_metrics.parse_error:
            continue

        for fn in file_metrics.functions:
            if fn.cyclomatic_complexity >= _HIGH_COMPLEXITY_THRESHOLD:
                complexity_confidence = score_from_threshold(
                    value=float(fn.cyclomatic_complexity),
                    threshold=float(_HIGH_COMPLEXITY_THRESHOLD),
                    base=0.58,
                    slope=0.22,
                    max_score=0.93,
                )
                findings.append(
                    _make_finding(
                        file_path=fn.file,
                        line_start=fn.line_start,
                        line_end=fn.line_end,
                        severity="medium",
                        title=f"Function '{fn.name}' is hard to reason about",
                        description=(f"{fn.name} has many decision paths (complexity={fn.cyclomatic_complexity}), which raises the risk of hidden branching bugs and difficult changes."),
                        suggestion=("Split the function into smaller helpers by responsibility and isolate branch-heavy sections behind descriptive names."),
                        confidence=complexity_confidence,
                    )
                )

            if fn.max_nesting_depth >= _HIGH_NESTING_THRESHOLD:
                nesting_confidence = score_from_threshold(
                    value=float(fn.max_nesting_depth),
                    threshold=float(_HIGH_NESTING_THRESHOLD),
                    base=0.56,
                    slope=0.2,
                    max_score=0.9,
                )

                if fn.cyclomatic_complexity >= _HIGH_COMPLEXITY_THRESHOLD:
                    complexity_confidence = score_from_threshold(
                        value=float(fn.cyclomatic_complexity),
                        threshold=float(_HIGH_COMPLEXITY_THRESHOLD),
                        base=0.58,
                        slope=0.22,
                        max_score=0.93,
                    )
                    nesting_confidence = blend_scores(
                        nesting_confidence,
                        complexity_confidence,
                        bonus=0.03,
                    )

                findings.append(
                    _make_finding(
                        file_path=fn.file,
                        line_start=fn.line_start,
                        line_end=fn.line_end,
                        severity="medium",
                        title=f"Function '{fn.name}' has deeply nested control flow",
                        description=(f"{fn.name} reaches nesting depth {fn.max_nesting_depth}, making the execution path harder to trace and maintain."),
                        suggestion=("Use guard clauses and early returns to flatten control flow, or extract inner branches into dedicated helpers."),
                        confidence=nesting_confidence,
                    )
                )

    return findings
