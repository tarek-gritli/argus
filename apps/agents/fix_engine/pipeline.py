"""
Fix Engine pipeline orchestrator.

Flow per finding:
    file_content
        └─► generator.generate_patch()   → FixProposal | None
                └─► validator.validate_patch()  → ValidationResult
                        └─► scorer.score_patch()      → float
                                └─► attach FixSchema to finding (if score ≥ threshold)

Findings without a matching file in `files_content`, or where generation /
validation / scoring fails, are returned unchanged so the rest of the review
result is never silently dropped.
"""

import logging

from shared.schemas.finding import FindingSchema, FixSchema

from .generator import generate_patch
from .scorer import score_patch
from .validator import validate_patch

logger = logging.getLogger(__name__)

# Minimum confidence score required to attach a fix to a finding.
# Patches below this threshold are logged and discarded rather than surfaced,
# to avoid noisy or incorrect auto-fix suggestions.
_CONFIDENCE_THRESHOLD = 0.6


def process_finding(finding: FindingSchema, file_content: str) -> FindingSchema:
    """
    Run a single finding through the full generation → validation → scoring
    pipeline. Returns the finding with `.fix` populated on success, or
    unchanged on any failure.
    """
    # --- Generation ---
    proposal = generate_patch(finding, file_content)
    if proposal is None:
        logger.info("No patch generated for finding '%s' — skipping", finding.title)
        return finding

    # --- Validation ---
    validation = validate_patch(file_content, proposal, finding)
    if not validation.is_valid:
        logger.info(
            "Patch for finding '%s' failed validation: %s",
            finding.title,
            validation.error_message,
        )
        return finding

    # --- Scoring ---
    confidence = score_patch(validation, finding)
    logger.debug(
        "Finding '%s' scored %.4f (threshold %.2f)",
        finding.title,
        confidence,
        _CONFIDENCE_THRESHOLD,
    )

    if confidence <= _CONFIDENCE_THRESHOLD:
        logger.info(
            "Patch for finding '%s' scored %.4f — below threshold, discarding",
            finding.title,
            confidence,
        )
        return finding

    # --- Attach fix ---
    # FixSchema.diff stores the replacement code (the "change" to apply).
    # Confidence is intentionally not stored on FixSchema — it served its
    # purpose as a gate; attaching it to the schema would imply it can be
    # re-evaluated later, which it cannot without re-running the pipeline.
    finding.fix = FixSchema(
        diff=proposal.patched_code,
        description=proposal.description,
    )
    logger.info(
        "Fix attached to finding '%s' (confidence=%.4f)",
        finding.title,
        confidence,
    )
    return finding


def run_fix_pipeline(
    findings: list[FindingSchema],
    files_content: dict[str, str],
) -> list[FindingSchema]:
    """
    Process a batch of findings through the Fix Engine.

    Args:
        findings:      All findings produced by the review agents.
        files_content: Mapping of file path → raw file content.
                       Only findings whose `.file` key is present here
                       will be processed; others are passed through untouched.

    Returns:
        The same list of findings, with `.fix` populated where a high-
        confidence patch was successfully generated and validated.
    """
    processed = fixed = skipped = 0

    for finding in findings:
        file_content = files_content.get(finding.file)

        if file_content is None:
            logger.debug(
                "File '%s' not in files_content — skipping finding '%s'",
                finding.file,
                finding.title,
            )
            skipped += 1
            continue

        process_finding(finding, file_content)
        processed += 1
        if finding.fix is not None:
            fixed += 1

    logger.info(
        "Fix pipeline complete — processed=%d fixed=%d skipped=%d total=%d",
        processed,
        fixed,
        skipped,
        len(findings),
    )
    return findings
