"""
Input schema for the quality agent.

AgentInput is what the orchestrator passes in.
The output is always list[FindingSchema] from packages/shared.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class AgentInput:
    """
    Everything the quality agent needs to do its job.

    Attributes:
        diff:           Full unified diff of the PR (all files, raw text).
        changed_files:  Mapping of repo-relative path → full file source AFTER the change.
                        Used for AST analysis. Only files present in the diff.
        repo_full_name: e.g. "org/repo"
        pr_number:      Pull request number.
        head_sha:       Commit SHA being reviewed.
        base_sha:       Base commit SHA.
        pr_title:       PR title (used for context injection into the prompt).
        pr_description: PR body text (optional).
    """

    diff: str
    changed_files: dict[str, str]
    repo_full_name: str
    pr_number: int
    head_sha: str
    base_sha: str
    pr_title: str = ""
    pr_description: str = ""
    # Phase 5: vector context will be injected here
    vector_context: list[str] = field(default_factory=list)
    historical_findings: list[dict] = field(default_factory=list)
