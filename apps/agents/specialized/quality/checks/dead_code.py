"""Dead code checks such as unused imports and unreachable branches."""

from __future__ import annotations

from typing import Any

from ..tools.ast_analyzer import StaticAnalysisResult
from ..tools.grep_patterns import PatternScanResult
from .confidence import score_from_count

FindingSchema = dict[str, Any]


def run_dead_code_checks(context: dict[str, Any]) -> list[FindingSchema]:
    static_result = context.get("static_result")
    pattern_result = context.get("pattern_result")
    findings: list[FindingSchema] = []

    if isinstance(static_result, StaticAnalysisResult):
        for file_metrics in static_result.files:
            if file_metrics.parse_error or not file_metrics.unused_imports:
                continue

            line_anchor = 1
            imports_preview = ", ".join(file_metrics.unused_imports[:3])
            unused_import_confidence = score_from_count(
                count=len(file_metrics.unused_imports),
                start=1,
                base=0.58,
                step=0.06,
                max_score=0.86,
            )
            findings.append(
                {
                    "agent": "quality",
                    "severity": "low",
                    "file": file_metrics.file,
                    "line_start": line_anchor,
                    "line_end": line_anchor,
                    "title": "Likely unused imports add noise",
                    "description": (f"Static analysis indicates imports that are never referenced in this file (for example: {imports_preview})."),
                    "suggestion": "Remove unused imports to reduce noise and import overhead.",
                    "confidence": unused_import_confidence,
                    "fix": None,
                }
            )

    if isinstance(pattern_result, PatternScanResult):
        for hit in pattern_result.hits:
            if hit.pattern_name != "commented_code":
                continue

            commented_code_confidence = 0.62
            if hit.matched_text.strip().startswith(("def ", "class ", "return ", "if ", "for ")):
                commented_code_confidence = 0.7

            findings.append(
                {
                    "agent": "quality",
                    "severity": "low",
                    "file": hit.file,
                    "line_start": hit.line,
                    "line_end": hit.line,
                    "title": "Commented-out code detected",
                    "description": ("Commented executable code is likely stale and can confuse future maintainers about the intended code path."),
                    "suggestion": ("Delete dead commented code and rely on VCS history for retrieval."),
                    "confidence": commented_code_confidence,
                    "fix": None,
                }
            )

    return findings
