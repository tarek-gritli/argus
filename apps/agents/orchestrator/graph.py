from __future__ import annotations

import operator
from typing import Annotated, Any, TypedDict

from context.bundle import ContextBundle
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
    context: ContextBundle


def _security_node(state: ReviewState) -> dict:
    return {"findings": security_analyze(state["files"], state["diff"], state["pr_payload"], context=state.get("context"))}


def _quality_node(state: ReviewState) -> dict:
    return {"findings": quality_analyze(state["files"], state["diff"], state["pr_payload"], context=state.get("context"))}


def _testing_node(state: ReviewState) -> dict:
    return {"findings": testing_analyze(state["files"], state["diff"], state["pr_payload"], context=state.get("context"))}


_VALID_PLANS = {"free", "pro", "team", "enterprise"}


def build_review_graph(plan: str = "free"):
    plan = plan.lower().strip()
    if plan not in _VALID_PLANS:
        raise ValueError(f"Unknown plan {plan!r}. Must be one of: {sorted(_VALID_PLANS)}")

    graph = StateGraph(ReviewState)
    graph.add_node("security", _security_node)
    graph.add_node("quality", _quality_node)
    graph.add_node("testing", _testing_node)
    graph.add_edge(START, "security")
    graph.add_edge(START, "quality")
    graph.add_edge(START, "testing")
    graph.add_edge("security", END)
    graph.add_edge("quality", END)
    graph.add_edge("testing", END)

    if plan in {"team", "enterprise"}:
        from specialized.ticket_compliance import analyze as tc_analyze

        def _doc_node(state: ReviewState) -> dict:
            return {"findings": documentation_analyze(state["files"], state["diff"], state["pr_payload"])}

        def _tc_node(state: ReviewState) -> dict:
            return {"findings": tc_analyze(state["files"], state["diff"], state["pr_payload"])}

        for name, node in [
            ("documentation", _doc_node),
            ("ticket_compliance", _tc_node),
        ]:
            graph.add_node(name, node)
            graph.add_edge(START, name)
            graph.add_edge(name, END)

    return graph.compile()


def run_review(
    files: list[Any],
    diff: str,
    pr_payload: PullRequestPayload,
    plan: str = "free",
    context: ContextBundle | None = None,
) -> list[FindingSchema]:
    app = build_review_graph(plan=plan)
    result = app.invoke(
        {
            "files": files,
            "diff": diff,
            "pr_payload": pr_payload,
            "findings": [],
            "context": context or ContextBundle.empty(),
        }
    )
    return result.get("findings", [])
