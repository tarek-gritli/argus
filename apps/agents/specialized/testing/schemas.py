"""
Input schema for the testing agent.
Mirrors the quality agent's AgentInput — same contract, different agent.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class AgentInput:
    """
    Everything the testing agent needs.

    Attributes:
        diff:           Full unified diff of the PR (all files, raw text).
        changed_files:  Mapping of repo-relative path → full file source AFTER the change.
                        Includes both source files AND test files modified in the PR.
        repo_full_name: e.g. "org/repo"
        pr_number:      Pull request number.
        head_sha:       Commit SHA being reviewed.
        base_sha:       Base commit SHA.
        pr_title:       PR title.
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
    # Phase 5: vector context injection
    vector_context: list[str] = field(default_factory=list)
    historical_findings: list[dict] = field(default_factory=list)
