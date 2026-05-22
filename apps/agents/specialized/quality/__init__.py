"""Quality specialized agent package."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from shared.schemas import FindingSchema

from .agent import run_quality_agent
from .schemas import AgentInput

if TYPE_CHECKING:
    from context.bundle import ContextBundle
    from integrations.github.schemas import PullRequestPayload

__all__ = ["analyze", "run_quality_agent"]


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


def _format_vector_context(chunks: list[dict]) -> list[str]:
    out = []
    for c in chunks:
        header = f"{c.get('filepath', '?')}:{c.get('start_line', '?')}-{c.get('end_line', '?')}"
        if c.get("function_name"):
            header += f"  fn={c['function_name']}"
        if c.get("class_name"):
            header += f"  class={c['class_name']}"
        out.append(f"# {header}\n{c.get('content', '')}")
    return out


def analyze(files: list[Any], diff: str, pr_payload: "PullRequestPayload", context: ContextBundle | None = None) -> list[FindingSchema]:
    """Adapter: build AgentInput from coordinator inputs and run the quality agent."""
    changed_files = {f.filename: _patch_to_source(f.patch or "") for f in files}
    agent_input = AgentInput(
        diff=diff,
        changed_files=changed_files,
        repo_full_name=pr_payload.repo_full_name,
        pr_number=pr_payload.pr_number,
        head_sha=pr_payload.head_sha,
        base_sha=pr_payload.base_sha,
        vector_context=_format_vector_context(context.similar_chunks) if context else [],
    )
    return run_quality_agent(agent_input)
