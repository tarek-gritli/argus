from unittest.mock import MagicMock, patch


def _make_mock_pr(pr_number: int = 123):
    mock_pr = MagicMock()
    mock_pr.number = pr_number
    mock_pr.head.repo.get_commit = MagicMock(return_value=MagicMock())
    return mock_pr


def _make_mock_file(filename: str = "src/auth.py", patch_text: str = "@@ -1 +1 @@ +bad code"):
    mock_file = MagicMock()
    mock_file.filename = filename
    mock_file.patch = patch_text
    return mock_file


def test_get_pr_returns_pull_request():
    """get_pr fetches the correct repo and PR via PyGithub."""
    mock_gh = MagicMock()
    mock_repo = MagicMock()
    mock_pr = _make_mock_pr()
    mock_gh.get_repo.return_value = mock_repo
    mock_repo.get_pull.return_value = mock_pr

    with patch("integrations.github.pr.get_installation_client", return_value=mock_gh):
        from integrations.github.pr import get_pr

        result = get_pr("owner/repo", 123, 42)

    mock_gh.get_repo.assert_called_once_with("owner/repo")
    mock_repo.get_pull.assert_called_once_with(123)
    assert result is mock_pr


def test_get_pr_files_returns_list():
    """get_pr_files materializes the paginated file list."""
    mock_pr = _make_mock_pr()
    mock_files = [_make_mock_file("a.py"), _make_mock_file("b.py")]
    mock_pr.get_files.return_value = iter(mock_files)

    from integrations.github.pr import get_pr_files

    result = get_pr_files(mock_pr)

    assert result == mock_files
    mock_pr.get_files.assert_called_once()


def test_post_issue_comment_calls_create():
    """post_issue_comment delegates to pr.create_issue_comment."""
    mock_pr = _make_mock_pr()

    from integrations.github.pr import post_issue_comment

    post_issue_comment(mock_pr, "## Review\nAll good.")

    mock_pr.create_issue_comment.assert_called_once_with("## Review\nAll good.")


def test_get_pr_diff_concatenates_patches():
    from unittest.mock import MagicMock

    from integrations.github.pr import get_pr_diff

    file1 = MagicMock()
    file1.filename = "src/foo.py"
    file1.patch = "@@ -1,3 +1,4 @@\n+new line\n context"

    file2 = MagicMock()
    file2.filename = "src/bar.py"
    file2.patch = "@@ -0,0 +1 @@\n+hello"

    pr = MagicMock()
    pr.get_files.return_value = [file1, file2]

    diff = get_pr_diff(pr)
    assert "--- a/src/foo.py" in diff
    assert "+++ b/src/foo.py" in diff
    assert "+new line" in diff
    assert "--- a/src/bar.py" in diff
    assert "+hello" in diff


def test_get_pr_diff_skips_files_without_patch():
    from unittest.mock import MagicMock

    from integrations.github.pr import get_pr_diff

    file1 = MagicMock()
    file1.filename = "image.png"
    file1.patch = None

    pr = MagicMock()
    pr.get_files.return_value = [file1]

    diff = get_pr_diff(pr)
    assert diff == ""


def test_post_review_comment_calls_create_review_comment():
    """post_review_comment posts inline comment on correct file and line."""
    mock_pr = _make_mock_pr()
    mock_commit = MagicMock()
    mock_pr.head.repo.get_commit.return_value = mock_commit

    from integrations.github.pr import post_review_comment

    post_review_comment(mock_pr, "Potential SQL injection", "abc123", "src/auth.py", 42)

    mock_pr.head.repo.get_commit.assert_called_once_with("abc123")
    mock_pr.create_review_comment.assert_called_once_with(
        body="Potential SQL injection",
        commit=mock_commit,
        path="src/auth.py",
        line=42,
        side="RIGHT",
    )
