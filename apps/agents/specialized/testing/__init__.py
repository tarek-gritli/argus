"""Testing specialized agent package."""

from __future__ import annotations

from typing import TYPE_CHECKING

from shared.schemas import FindingSchema

from .agent import run_testing_agent
from .schemas import AgentInput

if TYPE_CHECKING:
    from apps.agents.orchestrator.vcs import FileChange, UnifiedPayload

__all__ = ["analyze", "run_testing_agent"]


def _patch_to_source(patch: str) -> str:
    """Extract post-change source lines from a unified diff patch hunk.

    GitHub's File.patch contains only the changed context, not the full file.
    We strip diff metadata so ast.parse gets valid (partial) Python instead of
    hunk headers and removal lines that would cause SyntaxError.
    """
    lines = []
    for line in patch.splitlines():
        if line.startswith("@@") or line.startswith("---") or line.startswith("+++"):
            continue
        if line.startswith("-"):
            continue
        # context lines have a leading space; added lines have '+' — strip both
        lines.append(line[1:])
    return "\n".join(lines)


def analyze(files: list["FileChange"], diff: str, pr_payload: "UnifiedPayload") -> list[FindingSchema]:
    """Adapter: build AgentInput from coordinator inputs and run the testing agent."""
    changed_files = {f.filename: _patch_to_source(f.patch or "") for f in files}
    agent_input = AgentInput(
        diff=diff,
        changed_files=changed_files,
        repo_full_name=pr_payload.repo_id,
        pr_number=pr_payload.pr_id,
        head_sha=pr_payload.head_sha,
        base_sha=pr_payload.base_sha,
    )
    return run_testing_agent(agent_input)
