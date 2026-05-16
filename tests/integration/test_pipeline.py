"""
End-to-end pipeline test: real diff → real security scanners → coordinator formats comment.

GitHub API calls (get_pr, get_pr_files, post_issue_comment, get_pr_diff) are mocked so
this runs without credentials. Quality and testing LLM calls are also mocked — those
agents are covered by their own unit tests. Only the security agent runs for real (its
scanners are purely regex-based and need no credentials).
"""

from unittest.mock import MagicMock, patch

DIFF_WITH_FINDINGS = """\
--- a/src/auth.py
+++ b/src/auth.py
@@ -1,5 +1,10 @@
+import subprocess
+
+SECRET_KEY = "sk_live_ABC123DEF456GHI"
+
 def get_user(user_id):
-    return db.query(f"SELECT * FROM users WHERE id = {user_id}")
+    query = f"SELECT * FROM users WHERE id = {user_id}"
+    return db.execute(query)
+
+def run_cmd(cmd):
+    subprocess.run(cmd, shell=True)
"""

DIFF_CLEAN = """\
--- a/src/utils.py
+++ b/src/utils.py
@@ -1,3 +1,5 @@
+def add(a, b):
+    return a + b
"""


def _make_mock_files(diff: str) -> list[MagicMock]:
    """Build fake GitHub file objects from a raw diff string."""
    files = []
    current_file = None
    patch_lines = []

    for line in diff.splitlines():
        if line.startswith("+++ b/"):
            if current_file is not None:
                f = MagicMock()
                f.filename = current_file
                f.patch = "\n".join(patch_lines)
                files.append(f)
            current_file = line.removeprefix("+++ b/")
            patch_lines = []
        elif current_file is not None and not line.startswith("--- "):
            patch_lines.append(line)

    if current_file is not None:
        f = MagicMock()
        f.filename = current_file
        f.patch = "\n".join(patch_lines)
        files.append(f)

    return files


VALID_PAYLOAD = {
    "action": "opened",
    "repo_full_name": "owner/repo",
    "pr_number": 1,
    "head_sha": "abc123",
    "base_sha": "base456",
    "installation_id": 42,
}


def test_pipeline_detects_findings_and_posts_comment():
    """Real scanners find secrets + SAST issues; coordinator posts a formatted comment."""
    mock_pr = MagicMock()
    mock_files = _make_mock_files(DIFF_WITH_FINDINGS)

    with (
        patch("orchestrator.coordinator.get_pr", return_value=mock_pr),
        patch("orchestrator.coordinator.get_pr_files", return_value=mock_files),
        patch("orchestrator.coordinator.get_pr_diff", return_value=DIFF_WITH_FINDINGS),
        patch("orchestrator.coordinator.get_pr_file_content", return_value="mock file content"),
        patch("specialized.quality.agent._call_claude", return_value="[]"),
        patch("specialized.testing.agent._call_claude", return_value="[]"),
        patch("orchestrator.graph.documentation_analyze", return_value=[]),
        patch("orchestrator.coordinator.run_fix_pipeline") as mock_fix,
        patch("orchestrator.coordinator.post_findings_as_review"),
        patch("orchestrator.coordinator.post_issue_comment") as mock_post,
    ):

        def fake_run_fix(findings, files_content):
            from shared.schemas.finding import FixSchema

            for f in findings:
                if "Injection" in f.title:
                    f.fix = FixSchema(diff="safe code", description="Fixed injection")
            return findings

        mock_fix.side_effect = fake_run_fix

        from orchestrator.coordinator import run

        run(VALID_PAYLOAD)

    mock_post.assert_called_once()
    body: str = mock_post.call_args[0][1]

    assert "Security Review" in body
    assert "No issues found" not in body
    assert "Hardcoded Secret" in body
    assert any(term in body for term in ["Injection", "SUBPROCESS", "SQL"])

    # Assert fix formatting
    assert "<details>" in body
    assert "💡 Suggested Fix: <i>Fixed injection</i>" in body
    assert "```\nsafe code\n```" in body


def test_pipeline_clean_diff_posts_no_issues():
    """A diff with no security issues and no LLM findings produces the all-clear comment."""
    mock_pr = MagicMock()
    mock_files = _make_mock_files(DIFF_CLEAN)

    with (
        patch("orchestrator.coordinator.get_pr", return_value=mock_pr),
        patch("orchestrator.coordinator.get_pr_files", return_value=mock_files),
        patch("orchestrator.coordinator.get_pr_diff", return_value=DIFF_CLEAN),
        patch("orchestrator.coordinator.get_pr_file_content", return_value="mock file content"),
        patch("specialized.quality.agent._call_claude", return_value="[]"),
        patch("specialized.testing.agent._call_claude", return_value="[]"),
        patch("orchestrator.graph.documentation_analyze", return_value=[]),
        patch("orchestrator.coordinator.post_findings_as_review"),
        patch("orchestrator.coordinator.post_issue_comment") as mock_post,
    ):
        from orchestrator.coordinator import run

        run(VALID_PAYLOAD)

    mock_post.assert_called_once()
    body: str = mock_post.call_args[0][1]
    assert "No issues found" in body


def test_pipeline_comment_severity_ordering():
    """Findings are grouped critical → high → medium → low in the comment."""
    mock_pr = MagicMock()
    mock_files = _make_mock_files(DIFF_WITH_FINDINGS)

    with (
        patch("orchestrator.coordinator.get_pr", return_value=mock_pr),
        patch("orchestrator.coordinator.get_pr_files", return_value=mock_files),
        patch("orchestrator.coordinator.get_pr_diff", return_value=DIFF_WITH_FINDINGS),
        patch("orchestrator.coordinator.get_pr_file_content", return_value="mock file content"),
        patch("specialized.quality.agent._call_claude", return_value="[]"),
        patch("specialized.testing.agent._call_claude", return_value="[]"),
        patch("orchestrator.graph.documentation_analyze", return_value=[]),
        patch("orchestrator.coordinator.run_fix_pipeline", side_effect=lambda f, _: f),
        patch("orchestrator.coordinator.post_findings_as_review"),
        patch("orchestrator.coordinator.post_issue_comment") as mock_post,
    ):
        from orchestrator.coordinator import run

        run(VALID_PAYLOAD)

    body: str = mock_post.call_args[0][1]

    severity_order = ["CRITICAL", "HIGH", "MEDIUM", "LOW"]
    positions = {s: body.find(f"#### {s}") for s in severity_order if f"#### {s}" in body}
    found_sevs = [s for s in severity_order if s in positions]

    assert found_sevs == sorted(found_sevs, key=lambda s: severity_order.index(s))


def test_pipeline_empty_file_list_posts_warning():
    """No files in the PR → warning comment, agent never runs."""
    mock_pr = MagicMock()

    with (
        patch("orchestrator.coordinator.get_pr", return_value=mock_pr),
        patch("orchestrator.coordinator.get_pr_files", return_value=[]),
        patch("orchestrator.coordinator.post_issue_comment") as mock_post,
    ):
        from orchestrator.coordinator import run

        run(VALID_PAYLOAD)

    body: str = mock_post.call_args[0][1]
    assert "No changes detected" in body


def test_coordinator_calls_post_findings_as_review():
    """Coordinator calls post_findings_as_review with the head SHA after fix pipeline."""
    mock_pr = MagicMock()
    mock_files = _make_mock_files(DIFF_WITH_FINDINGS)

    with (
        patch("orchestrator.coordinator.get_pr", return_value=mock_pr),
        patch("orchestrator.coordinator.get_pr_files", return_value=mock_files),
        patch("orchestrator.coordinator.get_pr_diff", return_value=DIFF_WITH_FINDINGS),
        patch("orchestrator.coordinator.get_pr_file_content", return_value="mock file content"),
        patch("specialized.quality.agent._call_claude", return_value="[]"),
        patch("specialized.testing.agent._call_claude", return_value="[]"),
        patch("orchestrator.graph.documentation_analyze", return_value=[]),
        patch("orchestrator.coordinator.run_fix_pipeline", side_effect=lambda f, _: f),
        patch("orchestrator.coordinator.post_findings_as_review") as mock_review,
        patch("orchestrator.coordinator.post_issue_comment"),
    ):
        from orchestrator.coordinator import run

        run(VALID_PAYLOAD)

    mock_review.assert_called_once()
    _, findings_arg, sha_arg = mock_review.call_args[0]
    assert sha_arg == VALID_PAYLOAD["head_sha"]
    assert isinstance(findings_arg, list)


def test_post_findings_as_review_suggestion_format():
    """Findings with fixes are posted with ```suggestion``` blocks; others as plain comments."""
    from integrations.github.pr import post_findings_as_review
    from shared.schemas.finding import FindingSchema, FixSchema

    mock_pr = MagicMock()
    mock_pr.head.repo.get_commit.return_value = MagicMock()

    # Simulate a diff where line 3 of src/auth.py is in the PR
    mock_file = MagicMock()
    mock_file.filename = "src/auth.py"
    mock_file.patch = "@@ -1,4 +1,4 @@\n line1\n line2\n-old line\n+new line\n"
    mock_pr.get_files.return_value = [mock_file]

    finding_with_fix = FindingSchema(
        agent="security",
        severity="high",
        file="src/auth.py",
        line_start=3,
        line_end=3,
        title="SQL Injection",
        description="Unsafe query",
        confidence=0.9,
        fix=FixSchema(diff="safe_query(user_id)", description="Use parameterised query"),
    )
    finding_no_fix = FindingSchema(
        agent="security",
        severity="medium",
        file="src/auth.py",
        line_start=3,
        line_end=3,
        title="Hardcoded Secret",
        description="Secret in code",
        confidence=0.8,
    )

    post_findings_as_review(mock_pr, [finding_with_fix, finding_no_fix], "abc123")

    mock_pr.create_review.assert_called_once()
    comments = mock_pr.create_review.call_args[1]["comments"]
    assert len(comments) == 2

    fix_comment = next(c for c in comments if "SQL Injection" in c["body"])
    assert "```suggestion" in fix_comment["body"]
    assert "safe_query(user_id)" in fix_comment["body"]

    plain_comment = next(c for c in comments if "Hardcoded Secret" in c["body"])
    assert "```suggestion" not in plain_comment["body"]


def test_post_findings_as_review_skips_lines_outside_diff():
    """Findings on lines not in the PR diff are silently skipped."""
    from integrations.github.pr import post_findings_as_review
    from shared.schemas.finding import FindingSchema

    mock_pr = MagicMock()
    mock_pr.head.repo.get_commit.return_value = MagicMock()

    mock_file = MagicMock()
    mock_file.filename = "src/auth.py"
    mock_file.patch = "@@ -1,2 +1,2 @@\n line1\n line2\n"
    mock_pr.get_files.return_value = [mock_file]

    # Finding is on line 99 — not in the diff above
    finding = FindingSchema(
        agent="security",
        severity="high",
        file="src/auth.py",
        line_start=99,
        line_end=99,
        title="Issue",
        description="Some issue",
        confidence=0.9,
    )

    post_findings_as_review(mock_pr, [finding], "abc123")

    mock_pr.create_review.assert_not_called()
