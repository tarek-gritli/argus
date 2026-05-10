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


class TestFormatFindings:
    def test_format_groups_by_agent_and_severity(self):
        from orchestrator.coordinator import _format_findings

        findings = [
            _make_finding("security", "SQL Injection"),
            _make_finding("quality", "High complexity"),
            _make_finding("testing", "Missing test"),
        ]
        result = _format_findings(findings)
        assert "Security" in result
        assert "Quality" in result
        assert "Testing" in result
        assert "SQL Injection" in result
        assert "High complexity" in result
        assert "Missing test" in result

    def test_format_no_findings_returns_all_clear(self):
        from orchestrator.coordinator import _format_findings

        result = _format_findings([])
        assert "No issues" in result

    def test_format_severity_ordering(self):
        from orchestrator.coordinator import _format_findings
        from shared.schemas.finding import FindingSchema

        findings = [
            FindingSchema(
                agent="security",
                severity="low",
                file="f.py",
                line_start=1,
                line_end=1,
                title="Low issue",
                description="d",
                suggestion=None,
                confidence=0.6,
                fix=None,
            ),
            FindingSchema(
                agent="security",
                severity="critical",
                file="f.py",
                line_start=2,
                line_end=2,
                title="Critical issue",
                description="d",
                suggestion=None,
                confidence=0.9,
                fix=None,
            ),
        ]
        result = _format_findings(findings)
        assert result.index("Critical") < result.index("Low")

    def test_format_unknown_agent_findings_are_not_dropped(self):
        from orchestrator.coordinator import _format_findings
        from shared.schemas.finding import FindingSchema

        findings = [
            FindingSchema(
                agent="performance",
                severity="medium",
                file="f.py",
                line_start=1,
                line_end=1,
                title="Slow query",
                description="N+1 detected",
                suggestion=None,
                confidence=0.7,
                fix=None,
            ),
        ]
        result = _format_findings(findings)
        assert "Slow query" in result
        assert "Performance" in result


class TestPatchToSource:
    def test_strips_hunk_headers(self):
        from specialized.quality import _patch_to_source

        patch = "@@ -1,3 +1,4 @@\n+def foo():\n+    return 1\n context"
        result = _patch_to_source(patch)
        assert "@@" not in result

    def test_strips_removed_lines(self):
        from specialized.quality import _patch_to_source

        patch = "@@ -1,2 +1,2 @@\n-old_line\n+new_line"
        result = _patch_to_source(patch)
        assert "old_line" not in result
        assert "new_line" in result

    def test_keeps_context_lines(self):
        from specialized.quality import _patch_to_source

        patch = "@@ -1,3 +1,3 @@\n context_line\n+added\n-removed"
        result = _patch_to_source(patch)
        assert "context_line" in result

    def test_output_is_parseable_python(self):
        import ast

        from specialized.quality import _patch_to_source

        patch = "@@ -1,2 +1,3 @@\n x = 1\n+def foo(x):\n+    return x + 1"
        source = _patch_to_source(patch)
        ast.parse(source)  # must not raise

    def test_empty_patch_returns_empty_string(self):
        from specialized.quality import _patch_to_source

        assert _patch_to_source("") == ""

    def test_testing_adapter_has_same_helper(self):
        from specialized.testing import _patch_to_source

        patch = "@@ -0,0 +1,2 @@\n+def test_foo():\n+    assert True"
        source = _patch_to_source(patch)
        assert "def test_foo():" in source
        assert "@@" not in source
