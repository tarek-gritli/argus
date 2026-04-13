from github.File import File
from integrations.github import PullRequestPayload
from shared.schemas import FindingSchema


def analyze(files: list[File], payload: PullRequestPayload) -> list[FindingSchema]:
    """
    Security agent: analyzes a PR diff for security issues.

    Args:
        files: List of changed files from the PR (each has .filename and .patch)
        payload: PullRequestPayload with repo/PR metadata

    Returns:
        List of FindingSchema objects representing security findings.
        Empty list if no issues found.

    TODO: Implement LLM-based security analysis.
    This is a stub for your implementation.
    """
    raise NotImplementedError("Security agent analysis not yet implemented")
