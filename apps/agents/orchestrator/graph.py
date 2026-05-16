from __future__ import annotations

import operator
from typing import Annotated, Any, TypedDict

from integrations.github import PullRequestPayload
from langgraph.graph import END, START, StateGraph
from shared.schemas import FindingSchema
from specialized.documentation import analyze as documentation_analyze
from specialized.quality import analyze as quality_analyze
from specialized.security import analyze as security_analyze
from specialized.testing import analyze as testing_analyze


class ReviewState(TypedDict):
    files: list[Any]
    diff: str
    pr_payload: PullRequestPayload
    findings: Annotated[list[FindingSchema], operator.add]


def _security_node(state: ReviewState) -> dict:
    return {"findings": security_analyze(state["files"], state["diff"], state["pr_payload"])}


def _quality_node(state: ReviewState) -> dict:
    return {"findings": quality_analyze(state["files"], state["diff"], state["pr_payload"])}


def _testing_node(state: ReviewState) -> dict:
    return {"findings": testing_analyze(state["files"], state["diff"], state["pr_payload"])}


def _documentation_node(state: ReviewState) -> dict:
    return {"findings": documentation_analyze(state["files"], state["diff"], state["pr_payload"])}


def build_review_graph():
    graph = StateGraph(ReviewState)
    graph.add_node("security", _security_node)
    graph.add_node("quality", _quality_node)
    graph.add_node("testing", _testing_node)
    graph.add_node("documentation", _documentation_node)
    graph.add_edge(START, "security")
    graph.add_edge(START, "quality")
    graph.add_edge(START, "testing")
    graph.add_edge(START, "documentation")
    graph.add_edge("security", END)
    graph.add_edge("quality", END)
    graph.add_edge("testing", END)
    graph.add_edge("documentation", END)
    return graph.compile()


def run_review(
    files: list[Any],
    diff: str,
    pr_payload: PullRequestPayload,
) -> list[FindingSchema]:
    app = build_review_graph()
    result = app.invoke({"files": files, "diff": diff, "pr_payload": pr_payload, "findings": []})
    return result.get("findings", [])
