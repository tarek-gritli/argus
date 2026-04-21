"""
End-to-end pipeline test: real diff → real security scanners → coordinator formats comment.

GitHub API calls (get_pr, get_pr_files, post_issue_comment) are mocked so this runs
without credentials. Everything else — scanner, reflection, adapter, formatter — is real.
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
        patch("orchestrator.coordinator.post_issue_comment") as mock_post,
    ):
        from orchestrator.coordinator import run

        run(VALID_PAYLOAD)

    mock_post.assert_called_once()
    body: str = mock_post.call_args[0][1]

    assert "Security Review" in body
    assert "No security issues found" not in body
    assert "Hardcoded Secret" in body
    assert any(term in body for term in ["Injection", "SUBPROCESS", "SQL"])


def test_pipeline_clean_diff_posts_no_issues():
    """A diff with no security issues produces the all-clear comment."""
    mock_pr = MagicMock()
    mock_files = _make_mock_files(DIFF_CLEAN)

    with (
        patch("orchestrator.coordinator.get_pr", return_value=mock_pr),
        patch("orchestrator.coordinator.get_pr_files", return_value=mock_files),
        patch("orchestrator.coordinator.post_issue_comment") as mock_post,
    ):
        from orchestrator.coordinator import run

        run(VALID_PAYLOAD)

    mock_post.assert_called_once()
    body: str = mock_post.call_args[0][1]
    assert "No security issues found" in body


def test_pipeline_comment_severity_ordering():
    """Findings are grouped critical → high → medium → low in the comment."""
    mock_pr = MagicMock()
    mock_files = _make_mock_files(DIFF_WITH_FINDINGS)

    with (
        patch("orchestrator.coordinator.get_pr", return_value=mock_pr),
        patch("orchestrator.coordinator.get_pr_files", return_value=mock_files),
        patch("orchestrator.coordinator.post_issue_comment") as mock_post,
    ):
        from orchestrator.coordinator import run

        run(VALID_PAYLOAD)

    body: str = mock_post.call_args[0][1]

    severity_order = ["CRITICAL", "HIGH", "MEDIUM", "LOW"]
    positions = {s: body.find(f"### {s}") for s in severity_order if f"### {s}" in body}
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
