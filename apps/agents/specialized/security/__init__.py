from __future__ import annotations

from typing import TYPE_CHECKING, Any

from shared.schemas import FindingSchema

from .agent import run_security_agent
from .schemas import AgentTask, RepoConfig

if TYPE_CHECKING:
    from context.bundle import ContextBundle
    from integrations.github import PullRequestPayload

__all__ = ["analyze", "run_security_agent"]


def analyze(files: list[Any], diff: str, pr_payload: PullRequestPayload, context: ContextBundle | None = None) -> list[FindingSchema]:
    """
    Adapter: Convert coordinator's interface to agent's interface and back.

    Takes the pre-fetched unified diff and PR payload, converts to AgentTask,
    runs security agent, converts ReviewResult back to FindingSchema.
    """
    task = AgentTask(
        diff=diff,
        pr_number=pr_payload.pr_number,
        repo_id=pr_payload.repo_full_name,
        repo_config=RepoConfig(exempt_paths=["tests/", "fixtures/"]),
    )

    result = run_security_agent(task)

    findings = []
    for finding in result.findings:
        severity_str = finding.severity.value.lower()
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
