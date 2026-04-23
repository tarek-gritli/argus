from __future__ import annotations

from typing import Any, TypedDict

from integrations.github import PullRequestPayload
from langgraph.graph import END, START, StateGraph
from shared.schemas import FindingSchema
from specialized.security import analyze as security_analyze


class _ReviewStateRequired(TypedDict):
    files: list[Any]
    pr_payload: PullRequestPayload


class ReviewState(_ReviewStateRequired, total=False):
    """Shared state flowing through the graph."""

    findings: list[FindingSchema]


def _security_node(state: ReviewState) -> ReviewState:
    findings = security_analyze(state["files"], state["pr_payload"])
    return {
        "files": state["files"],
        "pr_payload": state["pr_payload"],
        "findings": list(state.get("findings", [])) + findings,
    }


def build_review_graph():
    """Build and compile the review graph."""
    graph = StateGraph(ReviewState)
    graph.add_node("security", _security_node)
    graph.add_edge(START, "security")
    graph.add_edge("security", END)
    return graph.compile()


def run_review(files: list[Any], pr_payload: PullRequestPayload) -> list[FindingSchema]:
    """Execute the compiled graph and return aggregated findings."""
    app = build_review_graph()
    result = app.invoke({"files": files, "pr_payload": pr_payload, "findings": []})
    return result.get("findings", [])
