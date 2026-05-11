from pydantic import BaseModel, Field


class FixProposal(BaseModel):
    """
    Represents a candidate fix returned by the generator.

    `original_snippet` captures the exact lines Claude was shown, which lets
    the scorer and any downstream tooling compare before/after without
    re-reading the original file.
    """

    patched_code: str
    description: str
    original_snippet: str = Field(
        default="",
        description="The original source lines that this patch replaces. Populated by the generator before calling Claude so the scorer can measure patch size and diff quality.",
    )


class ValidationResult(BaseModel):
    """
    Outcome of running the validator against a FixProposal.

    `patched_line_count` is stored so the scorer can penalise proposals
    that touch far more lines than the finding spans — a heuristic signal
    that Claude over-reached and the fix may be unsafe to auto-merge.
    """

    is_valid: bool
    error_message: str | None = None
    applied_patch: str | None = None
    patched_line_count: int = Field(
        default=0,
        description="Total number of lines in the fully-patched file. Used by the scorer to detect unexpectedly large rewrites.",
    )
