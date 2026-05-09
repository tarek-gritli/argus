"""Testing specialized agent package."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from shared.schemas import FindingSchema

from .agent import run_testing_agent
from .schemas import AgentInput

if TYPE_CHECKING:
    from integrations.github.schemas import PullRequestPayload

__all__ = ["analyze", "run_testing_agent"]


def analyze(files: list[Any], diff: str, pr_payload: "PullRequestPayload") -> list[FindingSchema]:
    """Adapter: build AgentInput from coordinator inputs and run the testing agent."""
    changed_files = {f.filename: (f.patch or "") for f in files}
    agent_input = AgentInput(
        diff=diff,
        changed_files=changed_files,
        repo_full_name=pr_payload.repo_full_name,
        pr_number=pr_payload.pr_number,
        head_sha=pr_payload.head_sha,
        base_sha=pr_payload.base_sha,
    )
    return run_testing_agent(agent_input)
