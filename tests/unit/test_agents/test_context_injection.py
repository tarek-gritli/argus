from unittest.mock import AsyncMock, patch

import pytest
from context.bundle import ContextBundle
from orchestrator.graph import ReviewState, build_review_graph


def test_review_state_has_context_field():
    state = ReviewState(
        files=[],
        diff="",
        pr_payload=None,
        findings=[],
        context=ContextBundle.empty(),
    )
    assert state["context"].similar_chunks == []


def test_build_review_graph_compiles_with_context_in_state():
    graph = build_review_graph(plan="free")
    assert graph is not None


@pytest.mark.asyncio
async def test_fetch_context_returns_bundle():
    from orchestrator.coordinator import _fetch_context

    with patch(
        "orchestrator.coordinator.search_similar",
        new=AsyncMock(
            return_value=[
                {
                    "filepath": "a.py",
                    "score": 0.9,
                    "content": "def foo(): pass",
                    "start_line": 1,
                    "end_line": 3,
                    "function_name": "foo",
                    "class_name": None,
                }
            ]
        ),
    ):
        bundle = await _fetch_context(repo_id="repo_abc", diff="def foo(): pass\n")

    assert len(bundle.similar_chunks) == 1
    assert bundle.repo_id == "repo_abc"


@pytest.mark.asyncio
async def test_fetch_context_returns_empty_on_outage():
    from orchestrator.coordinator import _fetch_context

    with patch(
        "orchestrator.coordinator.search_similar",
        new=AsyncMock(side_effect=Exception("Qdrant down")),
    ):
        bundle = await _fetch_context(repo_id="repo_abc", diff="")

    assert bundle == ContextBundle.empty()
