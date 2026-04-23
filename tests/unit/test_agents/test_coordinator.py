from unittest.mock import MagicMock, patch

import pytest
from shared.schemas import FindingSchema

VALID_PAYLOAD = {
    "action": "opened",
    "repo_full_name": "owner/repo",
    "pr_number": 123,
    "head_sha": "abc123",
    "base_sha": "base456",
    "installation_id": 42,
}

SAMPLE_FINDING = FindingSchema(
    agent="security",
    severity="high",
    file="src/auth.py",
    line_start=10,
    line_end=15,
    title="SQL Injection",
    description="User input not sanitized.",
    suggestion="Use parameterized queries.",
    confidence=0.95,
)


def _make_mock_pr():
    mock_pr = MagicMock()
    return mock_pr


def _make_mock_files(n: int = 2):
    files = []
    for i in range(n):
        f = MagicMock()
        f.filename = f"src/file{i}.py"
        f.patch = f"@@ -1 +1 @@ +code{i}"
        files.append(f)
    return files


def test_run_happy_path_posts_findings():
    """Coordinator fetches files, runs analysis, posts comment."""
    mock_pr = _make_mock_pr()
    mock_files = _make_mock_files()

    with (
        patch("orchestrator.coordinator.get_pr", return_value=mock_pr),
        patch("orchestrator.coordinator.get_pr_files", return_value=mock_files),
        patch("orchestrator.coordinator.run_review", return_value=[SAMPLE_FINDING]),
        patch("orchestrator.coordinator.post_issue_comment") as mock_post,
    ):
        from orchestrator.coordinator import run

        run(VALID_PAYLOAD)

    mock_post.assert_called_once()
    body = mock_post.call_args[0][1]
    assert "SQL Injection" in body
    assert "HIGH" in body


def test_run_no_files_posts_warning():
    """Empty file list posts a warning comment and skips analysis."""
    mock_pr = _make_mock_pr()

    with (
        patch("orchestrator.coordinator.get_pr", return_value=mock_pr),
        patch("orchestrator.coordinator.get_pr_files", return_value=[]),
        patch("orchestrator.coordinator.run_review") as mock_analyze,
        patch("orchestrator.coordinator.post_issue_comment") as mock_post,
    ):
        from orchestrator.coordinator import run

        run(VALID_PAYLOAD)

    mock_analyze.assert_not_called()
    mock_post.assert_called_once()
    body = mock_post.call_args[0][1]
    assert "No changes detected" in body


def test_run_no_findings_posts_clean_message():
    """No findings from analysis posts a clean bill of health."""
    mock_pr = _make_mock_pr()

    with (
        patch("orchestrator.coordinator.get_pr", return_value=mock_pr),
        patch("orchestrator.coordinator.get_pr_files", return_value=_make_mock_files()),
        patch("orchestrator.coordinator.run_review", return_value=[]),
        patch("orchestrator.coordinator.post_issue_comment") as mock_post,
    ):
        from orchestrator.coordinator import run

        run(VALID_PAYLOAD)

    body = mock_post.call_args[0][1]
    assert "No security issues found" in body


def test_run_raises_on_get_pr_failure():
    """If get_pr raises, the exception propagates out of run()."""
    with patch("orchestrator.coordinator.get_pr", side_effect=Exception("GitHub API down")):
        from orchestrator.coordinator import run

        with pytest.raises(Exception, match="GitHub API down"):
            run(VALID_PAYLOAD)


def test_format_findings_groups_by_severity():
    """_format_findings groups and orders findings correctly."""
    findings = [
        FindingSchema(
            agent="security",
            severity="low",
            file="a.py",
            line_start=1,
            line_end=2,
            title="Minor issue",
            description="Low severity.",
            confidence=0.5,
        ),
        FindingSchema(
            agent="security",
            severity="critical",
            file="b.py",
            line_start=5,
            line_end=10,
            title="Critical bug",
            description="Very bad.",
            confidence=0.99,
        ),
    ]

    from orchestrator.coordinator import _format_findings

    result = _format_findings(findings)

    assert result.index("CRITICAL") < result.index("LOW")
    assert "Critical bug" in result
    assert "Minor issue" in result


def test_format_findings_includes_suggestion():
    """_format_findings includes suggestion when present."""
    finding = FindingSchema(
        agent="security",
        severity="high",
        file="c.py",
        line_start=1,
        line_end=1,
        title="XSS",
        description="Unescaped output.",
        suggestion="Escape HTML.",
        confidence=0.8,
    )

    from orchestrator.coordinator import _format_findings

    result = _format_findings([finding])

    assert "Escape HTML." in result


def test_format_findings_empty_returns_clean():
    """Empty findings list returns clean message."""
    from orchestrator.coordinator import _format_findings

    result = _format_findings([])
    assert "No security issues found" in result
