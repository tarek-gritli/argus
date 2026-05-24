from __future__ import annotations

from typing import TYPE_CHECKING

from shared.schemas import FindingSchema

from .agent import run_security_agent
from .schemas import AgentTask, RepoConfig

if TYPE_CHECKING:
    from apps.agents.orchestrator.vcs import FileChange, UnifiedPayload

__all__ = ["analyze", "run_security_agent"]


def analyze(files: list["FileChange"], pr_payload: "UnifiedPayload") -> list[FindingSchema]:
    """
    Adapter: Convert coordinator's interface to agent's interface and back.

    Takes GitHub files and PR payload, converts to AgentTask, runs security agent,
    converts ReviewResult back to FindingSchema for coordinator.
    """

    # Build diff from files
    diff = _build_diff_from_files(files)

    # Create AgentTask for the security agent
    task = AgentTask(
        diff=diff,
        pr_number=pr_payload.pr_id,
        repo_id=pr_payload.repo_id,
        repo_config=RepoConfig(exempt_paths=["tests/", "fixtures/"]),
    )

    # Run the security agent
    result = run_security_agent(task)

    # Convert Finding objects to FindingSchema
    findings = []
    for finding in result.findings:
        severity_str = finding.severity.value.lower()  # CRITICAL → critical
        findings.append(
            FindingSchema(
                agent="security",
                severity=severity_str,  # type: ignore
                file=finding.file,
                line_start=finding.line,
                line_end=finding.line,
                title=finding.category,
                description=finding.message,
                suggestion=finding.suggested_fix,
                confidence=finding.confidence,
                fix=None,
            )
        )

    return findings


def _build_diff_from_files(files: list["FileChange"]) -> str:
    """Build unified diff string from GitHub API file objects."""
    diff_lines = []

    for file in files:
        # Add file header
        diff_lines.append(f"--- a/{file.filename}")
        diff_lines.append(f"+++ b/{file.filename}")

        # Add patch content
        if file.patch:
            diff_lines.append(file.patch)

    return "\n".join(diff_lines)
