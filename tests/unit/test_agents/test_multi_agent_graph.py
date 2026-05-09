"""Tests for the multi-agent LangGraph graph wiring."""

from __future__ import annotations

from unittest.mock import MagicMock, patch


def _make_pr_payload(repo="org/repo", pr_number=1, head="abc", base="def", installation_id=42):
    from integrations.github.schemas import PullRequestPayload

    return PullRequestPayload(
        repo_full_name=repo,
        pr_number=pr_number,
        head_sha=head,
        base_sha=base,
        installation_id=installation_id,
        action="opened",
    )


def _make_finding(agent: str, title: str = "Test finding"):
    from shared.schemas.finding import FindingSchema

    return FindingSchema(
        agent=agent,
        severity="medium",
        file="src/foo.py",
        line_start=1,
        line_end=1,
        title=title,
        description="desc",
        suggestion=None,
        confidence=0.8,
        fix=None,
    )


class TestBuildReviewGraph:
    def test_graph_has_all_three_agent_nodes(self):
        from orchestrator.graph import build_review_graph

        graph = build_review_graph()
        assert "security" in graph.get_graph().nodes
        assert "quality" in graph.get_graph().nodes
        assert "testing" in graph.get_graph().nodes

    def test_run_review_aggregates_findings_from_all_agents(self):
        sec_finding = _make_finding("security")
        qual_finding = _make_finding("quality")
        test_finding = _make_finding("testing")

        with (
            patch("orchestrator.graph.security_analyze", return_value=[sec_finding]),
            patch("orchestrator.graph.quality_analyze", return_value=[qual_finding]),
            patch("orchestrator.graph.testing_analyze", return_value=[test_finding]),
        ):
            from orchestrator.graph import run_review

            findings = run_review(
                files=[MagicMock()],
                diff="+ some diff",
                pr_payload=_make_pr_payload(),
            )

        agents = {f.agent for f in findings}
        assert agents == {"security", "quality", "testing"}
        assert len(findings) == 3

    def test_run_review_tolerates_empty_agent_results(self):
        with (
            patch("orchestrator.graph.security_analyze", return_value=[]),
            patch("orchestrator.graph.quality_analyze", return_value=[]),
            patch("orchestrator.graph.testing_analyze", return_value=[]),
        ):
            from orchestrator.graph import run_review

            findings = run_review(
                files=[MagicMock()],
                diff="",
                pr_payload=_make_pr_payload(),
            )
        assert findings == []
