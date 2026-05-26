"""Duplication checks for repeated logic and copy-pasted blocks."""

from __future__ import annotations

from typing import Any

from ...confidence import score_from_count
from ..tools.ast_analyzer import StaticAnalysisResult

FindingSchema = dict[str, Any]


def run_duplication_checks(context: dict[str, Any]) -> list[FindingSchema]:
    static_result = context.get("static_result")
    if not isinstance(static_result, StaticAnalysisResult):
        return []

    findings: list[FindingSchema] = []

    for file_metrics in static_result.files:
        duplicate_count = len(file_metrics.duplicate_block_hashes)
        if file_metrics.parse_error or duplicate_count == 0:
            continue

        line_anchor = 1
        severity = "high" if duplicate_count >= 3 else "medium"
        confidence = score_from_count(
            count=duplicate_count,
            start=1,
            base=0.6,
            step=0.08,
            max_score=0.9,
        )

        findings.append(
            {
                "agent": "quality",
                "severity": severity,
                "file": file_metrics.file,
                "line_start": line_anchor,
                "line_end": line_anchor,
                "title": "Potential copy-pasted logic detected",
                "description": (f"Detected {duplicate_count} repeated code block patterns in this file, which increases maintenance cost and bug propagation risk."),
                "suggestion": ("Extract repeated blocks into a shared helper or utility with a single source of truth."),
                "confidence": confidence,
                "fix": None,
            }
        )

    return findings
