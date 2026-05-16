"""Documentation specialized agent package."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from shared.schemas import FindingSchema

from .agent import run_documentation_agent
from .schemas import AgentInput

if TYPE_CHECKING:
    from integrations.github.schemas import PullRequestPayload

__all__ = ["analyze", "run_documentation_agent"]


def _patch_to_source(patch: str) -> str:
    lines = []
    for line in patch.splitlines():
        if line.startswith("@@") or line.startswith("---") or line.startswith("+++"):
            continue
        if line.startswith("-"):
            continue
        # Only strip the diff marker (+/space) — leave metadata lines like
        # "\ No newline at end of file" untouched.
        lines.append(line[1:] if line and line[0] in (" ", "+") else line)
    return "\n".join(lines)


def analyze(files: list[Any], diff: str, pr_payload: "PullRequestPayload") -> list[FindingSchema]:
    """Adapter: build AgentInput from coordinator inputs and run the documentation agent."""
    changed_files = {f.filename: _patch_to_source(f.patch or "") for f in files}
    agent_input = AgentInput(
        diff=diff,
        changed_files=changed_files,
        repo_full_name=pr_payload.repo_full_name,
        pr_number=pr_payload.pr_number,
        head_sha=pr_payload.head_sha,
        base_sha=pr_payload.base_sha,
        pr_title=getattr(pr_payload, "pr_title", ""),
        pr_description=getattr(pr_payload, "pr_description", ""),
    )
    return run_documentation_agent(agent_input)
