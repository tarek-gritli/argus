import logging

from shared.schemas.finding import FindingSchema

from .schemas import ValidationResult

logger = logging.getLogger(__name__)

# Severity penalty: higher severity findings are harder to auto-fix safely,
# so we discount confidence to avoid auto-merging risky patches.
_SEVERITY_PENALTY: dict[str, float] = {
    "critical": 0.15,
    "high": 0.10,
    "medium": 0.05,
    "low": 0.0,
    "info": 0.0,  # informational findings are low-risk to auto-fix
}

# If the patch touches this many times more lines than the finding spans,
# Claude likely over-reached. Apply an additional confidence penalty.
_CHURN_RATIO_THRESHOLD = 10
_CHURN_PENALTY = 0.15


def score_patch(validation: ValidationResult, finding: FindingSchema) -> float:
    if not validation.is_valid:
        return 0.0

    # Start from a high baseline — syntax validity is a strong signal.
    confidence = 0.9

    # Discount based on how dangerous a wrong fix would be.
    severity_penalty = _SEVERITY_PENALTY.get(finding.severity, 0.05)
    confidence -= severity_penalty

    # Penalise patches that introduce far more lines than the finding spans.
    # A 2-line finding that produces a 200-line patch is suspicious.
    finding_span = max(1, finding.line_end - finding.line_start + 1)
    if validation.patch_line_count > 0:
        churn_ratio = validation.patch_line_count / finding_span
        if churn_ratio > _CHURN_RATIO_THRESHOLD:
            logger.debug(
                "High churn ratio %.1f for finding '%s' — applying penalty",
                churn_ratio,
                finding.title,
            )
            confidence -= _CHURN_PENALTY

    return round(min(1.0, max(0.0, confidence)), 4)
