import ast
import logging

from shared.schemas.finding import FindingSchema

from .schemas import FixProposal, ValidationResult

logger = logging.getLogger(__name__)


def validate_patch(original_code: str, proposal: FixProposal, finding: FindingSchema) -> ValidationResult:
    lines = original_code.splitlines(keepends=True)

    # line_start / line_end are 1-indexed; end is inclusive.
    start_idx = finding.line_start - 1
    end_idx = finding.line_end  # exclusive for slicing

    if start_idx < 0 or end_idx > len(lines):
        return ValidationResult(
            is_valid=False,
            error_message=(f"Finding line numbers ({finding.line_start}-{finding.line_end}) are out of bounds for file with {len(lines)} lines."),
        )

    # Strip leading/trailing newlines from the proposal so we never introduce
    # double blank lines at the splice boundary, then re-add exactly one
    # trailing newline to keep the file well-formed.
    patched_code = proposal.patched_code.strip("\n")

    if patched_code:
        # Non-empty patch: replace the flagged lines.
        replacement = [patched_code + "\n"]
    else:
        # Empty patched_code means "delete the flagged lines entirely"
        # (e.g. removing an unused import).
        replacement = []

    patched_lines = lines[:start_idx] + replacement + lines[end_idx:]
    patched_content = "".join(patched_lines)
    line_count = len(patched_content.splitlines())

    if finding.file.endswith(".py"):
        try:
            ast.parse(patched_content)
        except SyntaxError as exc:
            logger.warning(
                "Patch for finding '%s' produced a SyntaxError: %s",
                finding.title,
                exc,
            )
            return ValidationResult(
                is_valid=False,
                error_message=f"SyntaxError: {exc}",
                patched_line_count=line_count,
            )

    return ValidationResult(
        is_valid=True,
        applied_patch=patched_content,
        patched_line_count=line_count,
    )
