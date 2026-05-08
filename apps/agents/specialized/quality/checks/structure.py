"""Structure checks for naming, magic numbers, and long functions."""

from __future__ import annotations

from typing import Any

from ..tools.ast_analyzer import StaticAnalysisResult
from ..tools.grep_patterns import PatternScanResult
from .confidence import blend_scores, score_from_count, score_from_threshold

FindingSchema = dict[str, Any]


_LONG_FUNCTION_THRESHOLD = 80
_MAGIC_NUMBER_CLUSTER_THRESHOLD = 4


def _line_anchor_for_file(file_path: str, static_result: StaticAnalysisResult) -> int:
    for file_metrics in static_result.files:
        if file_metrics.file != file_path:
            continue
        if file_metrics.functions:
            return file_metrics.functions[0].line_start
    return 1


def run_structure_checks(context: dict[str, Any]) -> list[FindingSchema]:
    static_result = context.get("static_result")
    pattern_result = context.get("pattern_result")
    findings: list[FindingSchema] = []

    if isinstance(static_result, StaticAnalysisResult):
        for file_metrics in static_result.files:
            if file_metrics.parse_error:
                continue

            if len(file_metrics.magic_numbers) >= _MAGIC_NUMBER_CLUSTER_THRESHOLD:
                first_line = file_metrics.magic_numbers[0][0]
                magic_number_confidence = score_from_count(
                    count=len(file_metrics.magic_numbers),
                    start=_MAGIC_NUMBER_CLUSTER_THRESHOLD,
                    base=0.58,
                    step=0.05,
                    max_score=0.86,
                )
                findings.append(
                    {
                        "agent": "quality",
                        "severity": "medium",
                        "file": file_metrics.file,
                        "line_start": first_line,
                        "line_end": first_line,
                        "title": "Multiple unexplained numeric constants",
                        "description": (f"Found {len(file_metrics.magic_numbers)} non-trivial numeric literals, which can obscure domain intent and make future changes error-prone."),
                        "suggestion": ("Replace repeated literals with named constants that encode business meaning."),
                        "confidence": magic_number_confidence,
                        "fix": None,
                    }
                )

            for fn in file_metrics.functions:
                if fn.line_count < _LONG_FUNCTION_THRESHOLD:
                    continue

                length_confidence = score_from_threshold(
                    value=float(fn.line_count),
                    threshold=float(_LONG_FUNCTION_THRESHOLD),
                    base=0.58,
                    slope=0.16,
                    max_score=0.9,
                )
                if fn.cyclomatic_complexity >= 10:
                    complexity_confidence = score_from_threshold(
                        value=float(fn.cyclomatic_complexity),
                        threshold=10.0,
                        base=0.58,
                        slope=0.2,
                        max_score=0.92,
                    )
                    length_confidence = blend_scores(
                        length_confidence,
                        complexity_confidence,
                        bonus=0.02,
                    )

                findings.append(
                    {
                        "agent": "quality",
                        "severity": "medium",
                        "file": fn.file,
                        "line_start": fn.line_start,
                        "line_end": fn.line_end,
                        "title": f"Function '{fn.name}' is too long",
                        "description": (f"{fn.name} spans {fn.line_count} lines, making it harder to understand and test in isolation."),
                        "suggestion": ("Split this function into smaller units grouped by single responsibility, keeping orchestration at the top level."),
                        "confidence": length_confidence,
                        "fix": None,
                    }
                )

    if isinstance(pattern_result, PatternScanResult) and isinstance(
        static_result,
        StaticAnalysisResult,
    ):
        for hit in pattern_result.hits:
            if hit.pattern_name == "long_line":
                line_length_confidence = 0.55
                if len(hit.matched_text) >= 150:
                    line_length_confidence = 0.62

                findings.append(
                    {
                        "agent": "quality",
                        "severity": "info",
                        "file": hit.file,
                        "line_start": hit.line,
                        "line_end": hit.line,
                        "title": "Overly long added line",
                        "description": ("The added line exceeds the configured readability threshold and may be hard to review and maintain."),
                        "suggestion": ("Wrap the statement or extract sub-expressions into named variables."),
                        "confidence": line_length_confidence,
                        "fix": None,
                    }
                )
            elif hit.pattern_name == "mutable_default_arg":
                line_anchor = hit.line
                if line_anchor <= 0:
                    line_anchor = _line_anchor_for_file(hit.file, static_result)

                mutable_default_confidence = 0.9

                findings.append(
                    {
                        "agent": "quality",
                        "severity": "high",
                        "file": hit.file,
                        "line_start": line_anchor,
                        "line_end": line_anchor,
                        "title": "Mutable default argument in function signature",
                        "description": ("Using a mutable default like [] or {} can leak state across calls and produce surprising behavior."),
                        "suggestion": ("Use None as the default and initialize the mutable value inside the function body."),
                        "confidence": mutable_default_confidence,
                        "fix": None,
                    }
                )

    return findings
