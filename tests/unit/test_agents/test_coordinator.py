from unittest.mock import AsyncMock, MagicMock, patch

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
        patch("orchestrator.coordinator.get_pr_diff", return_value="+ some diff"),
        patch("orchestrator.coordinator.run_review", return_value=[SAMPLE_FINDING]),
        patch("orchestrator.coordinator.post_issue_comment") as mock_post,
    ):
        from orchestrator.coordinator import run

        run(VALID_PAYLOAD)

    mock_post.assert_called_once()
    body = mock_post.call_args[0][1]
    assert "SQL Injection" in body
    assert "HIGH" in body or "high" in body.lower()


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
        patch("orchestrator.coordinator.get_pr_diff", return_value=""),
        patch("orchestrator.coordinator.run_review", return_value=[]),
        patch("orchestrator.coordinator.post_issue_comment") as mock_post,
    ):
        from orchestrator.coordinator import run

        run(VALID_PAYLOAD)

    body = mock_post.call_args[0][1]
    assert "No issues" in body


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
    assert "No issues" in result


def test_run_persists_review_and_findings_when_org_id_present():
    """When org_id is in payload, coordinator should persist Review + Findings to DB."""
    mock_pr = _make_mock_pr()
    mock_files = _make_mock_files()

    mock_repo = MagicMock()
    mock_repo.id = "repo-uuid"

    mock_session = AsyncMock()
    mock_session.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=mock_repo)))
    mock_session.flush = AsyncMock()
    mock_session.commit = AsyncMock()
    mock_session.add = MagicMock()

    mock_ctx = AsyncMock()
    mock_ctx.__aenter__ = AsyncMock(return_value=mock_session)
    mock_ctx.__aexit__ = AsyncMock(return_value=False)

    payload_with_org = {**VALID_PAYLOAD, "org_id": "org-123"}

    with (
        patch("orchestrator.coordinator.get_pr", return_value=mock_pr),
        patch("orchestrator.coordinator.get_pr_files", return_value=mock_files),
        patch("orchestrator.coordinator.get_pr_diff", return_value="+ some diff"),
        patch("orchestrator.coordinator.get_pr_file_content", return_value="code"),
        patch("orchestrator.coordinator.run_review", return_value=[SAMPLE_FINDING]),
        patch("orchestrator.coordinator.run_fix_pipeline", return_value=[SAMPLE_FINDING]),
        patch("orchestrator.coordinator.post_findings_as_review"),
        patch("orchestrator.coordinator.post_issue_comment"),
        patch("orchestrator.coordinator._check_quota", new=AsyncMock(return_value=True)),
        patch("orchestrator.coordinator.fresh_session_context", return_value=mock_ctx),
    ):
        from orchestrator.coordinator import run

        run(payload_with_org)

    assert mock_session.add.called
    assert mock_session.commit.called


def test_quota_exceeded_posts_comment_and_returns():
    mock_pr = _make_mock_pr()

    mock_billing = MagicMock()
    mock_billing.plan = "free"
    mock_billing.reviews_used_this_month = 50
    mock_billing.monthly_limit = 50

    with (
        patch("orchestrator.coordinator.get_pr", return_value=mock_pr),
        patch("orchestrator.coordinator.get_pr_files", return_value=_make_mock_files()),
        patch("orchestrator.coordinator.get_org_billing", new=AsyncMock(return_value=mock_billing)),
        patch("orchestrator.coordinator.check_and_increment_quota", new=AsyncMock(return_value=False)),
        patch("orchestrator.coordinator.run_review") as mock_review,
        patch("orchestrator.coordinator.post_issue_comment") as mock_post,
        patch("orchestrator.coordinator.fresh_session_context", return_value=_make_session_ctx()),
    ):
        from orchestrator.coordinator import run

        run({**VALID_PAYLOAD, "org_id": "o1"})

    mock_review.assert_not_called()
    mock_post.assert_called_once()
    assert "quota" in mock_post.call_args[0][1].lower()


def _make_session_ctx():
    mock_session = AsyncMock()
    mock_ctx = AsyncMock()
    mock_ctx.__aenter__ = AsyncMock(return_value=mock_session)
    mock_ctx.__aexit__ = AsyncMock(return_value=False)
    return mock_ctx


def test_run_skips_persist_when_no_org_id():
    """When org_id is absent, coordinator skips DB writes."""
    mock_pr = _make_mock_pr()
    mock_files = _make_mock_files()

    with (
        patch("orchestrator.coordinator.get_pr", return_value=mock_pr),
        patch("orchestrator.coordinator.get_pr_files", return_value=mock_files),
        patch("orchestrator.coordinator.get_pr_diff", return_value="+ some diff"),
        patch("orchestrator.coordinator.get_pr_file_content", return_value="code"),
        patch("orchestrator.coordinator.run_review", return_value=[SAMPLE_FINDING]),
        patch("orchestrator.coordinator.run_fix_pipeline", return_value=[SAMPLE_FINDING]),
        patch("orchestrator.coordinator.post_findings_as_review"),
        patch("orchestrator.coordinator.post_issue_comment"),
        patch("orchestrator.coordinator.fresh_session_context") as mock_sc,
    ):
        from orchestrator.coordinator import run

        run(VALID_PAYLOAD)  # no org_id

    mock_sc.assert_not_called()
