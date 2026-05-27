"""Shared confidence/scoring utilities for specialized agents.

This module centralizes confidence normalization, threshold checks, and
severity ordering so all agent validators use the same mechanics.
"""

from __future__ import annotations

from typing import Any

VALID_SEVERITIES = frozenset({"critical", "high", "medium", "low", "info"})
SEVERITY_WEIGHT = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}


def clamp(value: float, minimum: float = 0.0, maximum: float = 1.0) -> float:
    """Clamp a numeric value into a closed interval."""
    return max(minimum, min(maximum, value))


def coerce_confidence(value: Any) -> float | None:
    """Convert unknown input into confidence float [0, 1], or None on failure."""
    try:
        raw = float(value)
    except (TypeError, ValueError):
        return None
    return clamp(raw)


def confidence_at_or_above(confidence: float, floor: float) -> bool:
    """Return True when confidence satisfies floor after clamping."""
    return clamp(confidence) >= clamp(floor)


def scale_confidence(confidence: float, factor: float, precision: int = 3) -> float:
    """Scale confidence by a factor and round to fixed precision."""
    scaled = clamp(confidence) * factor
    return round(clamp(scaled), precision)


def normalize_severity(value: Any, default: str = "medium") -> str:
    """Normalize severity text to one of VALID_SEVERITIES."""
    if isinstance(value, str) and value in VALID_SEVERITIES:
        return value
    return default


def sort_by_severity_then_confidence(findings: list[dict[str, Any]]) -> None:
    """Sort findings in-place by severity and confidence descending."""
    findings.sort(
        key=lambda f: (
            SEVERITY_WEIGHT.get(str(f.get("severity", "")).lower(), 5),
            -float(f.get("confidence", 0.0)),
        )
    )


def score_from_threshold(
    *,
    value: float,
    threshold: float,
    base: float = 0.55,
    slope: float = 0.2,
    max_score: float = 0.92,
) -> float:
    """Score confidence from how far a value exceeds a threshold."""
    if threshold <= 0:
        return clamp(base)

    over_ratio = max(0.0, (value - threshold) / threshold)
    return clamp(base + (over_ratio * slope), minimum=0.5, maximum=max_score)


def score_from_count(
    *,
    count: int,
    start: int,
    base: float = 0.55,
    step: float = 0.06,
    max_score: float = 0.9,
) -> float:
    """Score confidence from count-based evidence above a start threshold."""
    if count <= start:
        return clamp(base, minimum=0.5, maximum=max_score)

    return clamp(base + ((count - start) * step), minimum=0.5, maximum=max_score)


def blend_scores(*scores: float, bonus: float = 0.0) -> float:
    """Blend multiple confidence signals and apply a bounded bonus."""
    if not scores:
        return 0.5

    avg = sum(scores) / len(scores)
    return clamp(avg + bonus, minimum=0.5, maximum=0.95)
