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


def test_get_pr_files_filters_ignored_and_patchless_files():
    """get_pr_files skips ignored dirs, lock files, binaries, and patch-less files."""
    mock_pr = _make_mock_pr()
    keep_file = _make_mock_file("src/app.py")
    ignored_dir_file = _make_mock_file("node_modules/pkg/index.js")
    ignored_generated_file = _make_mock_file("dist/app.min.js")
    ignored_lock_file = _make_mock_file("pnpm-lock.yaml")
    ignored_binary_file = _make_mock_file("assets/logo.png")
    patchless_file = _make_mock_file("src/image.png")
    patchless_file.patch = None
    mock_pr.get_files.return_value = [
        keep_file,
        ignored_dir_file,
        ignored_generated_file,
        ignored_lock_file,
        ignored_binary_file,
        patchless_file,
    ]

    from integrations.github.pr import get_pr_files

    result = get_pr_files(mock_pr)

    assert result == [keep_file]


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


def test_get_pr_diff_with_empty_files_iterable():
    """Passing an empty iterable for `files` returns empty diff."""
    from unittest.mock import MagicMock

    from integrations.github.pr import get_pr_diff

    pr = MagicMock()
    # files argument is an empty list
    diff = get_pr_diff(pr, files=[])
    assert diff == ""


def test_get_pr_diff_with_generator_and_patchless_items():
    """Ensure generator inputs are handled and patchless items are skipped."""
    from unittest.mock import MagicMock

    from integrations.github.pr import get_pr_diff

    file_with_patch = MagicMock()
    file_with_patch.filename = "src/ok.py"
    file_with_patch.patch = "@@ -1 +1 @@\n+ok"

    file_without_patch = MagicMock()
    file_without_patch.filename = "src/nope.py"
    file_without_patch.patch = None

    def gen():
        yield file_without_patch
        yield file_with_patch

    pr = MagicMock()

    diff = get_pr_diff(pr, files=gen())
    assert "ok" in diff
    assert "nope" not in diff


def test_get_pr_diff_filters_ignored_paths():
    from unittest.mock import MagicMock

    from integrations.github.pr import get_pr_diff

    ignored = MagicMock()
    ignored.filename = "node_modules/pkg/index.js"
    ignored.patch = "@@ -1 +1 @@\n+ignored"

    kept = MagicMock()
    kept.filename = "src/main.py"
    kept.patch = "@@ -1 +1 @@\n+kept"

    pr = MagicMock()
    pr.get_files.return_value = [ignored, kept]

    diff = get_pr_diff(pr)

    assert "ignored" not in diff
    assert "kept" in diff


def test_get_pr_diff_filters_lock_and_binary_files():
    from unittest.mock import MagicMock

    from integrations.github.pr import get_pr_diff

    lock_file = MagicMock()
    lock_file.filename = "package-lock.json"
    lock_file.patch = "@@ -1 +1 @@\n+ignored-lock"

    binary_file = MagicMock()
    binary_file.filename = "assets/icon.webp"
    binary_file.patch = "@@ -1 +1 @@\n+ignored-binary"

    kept = MagicMock()
    kept.filename = "src/main.py"
    kept.patch = "@@ -1 +1 @@\n+kept"

    pr = MagicMock()
    pr.get_files.return_value = [lock_file, binary_file, kept]

    diff = get_pr_diff(pr)

    assert "ignored-lock" not in diff
    assert "ignored-binary" not in diff
    assert "kept" in diff


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
