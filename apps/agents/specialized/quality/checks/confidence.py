"""Confidence scoring helpers for deterministic quality checks."""

from __future__ import annotations


def _clamp(value: float, minimum: float = 0.0, maximum: float = 1.0) -> float:
    return max(minimum, min(maximum, value))


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
        return _clamp(base)

    over_ratio = max(0.0, (value - threshold) / threshold)
    return _clamp(base + (over_ratio * slope), minimum=0.5, maximum=max_score)


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
        return _clamp(base, minimum=0.5, maximum=max_score)

    return _clamp(base + ((count - start) * step), minimum=0.5, maximum=max_score)


def blend_scores(*scores: float, bonus: float = 0.0) -> float:
    """Blend multiple signals and apply a small bounded bonus."""
    if not scores:
        return 0.5

    avg = sum(scores) / len(scores)
    return _clamp(avg + bonus, minimum=0.5, maximum=0.95)
