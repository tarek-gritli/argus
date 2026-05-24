from unittest.mock import MagicMock, patch

from gitlab.exceptions import GitlabGetError
from integrations.gitlab.mr import (
    get_mr,
    get_mr_diff,
    get_mr_file_content,
    get_mr_files,
    post_findings_as_review,
    post_issue_comment,
    post_review_comment,
)


def _make_mock_mr(project_id: int = 1, mr_iid: int = 2):
    mock_mr = MagicMock()
    mock_mr.project_id = project_id
    mock_mr.iid = mr_iid
    mock_mr.sha = "head_sha_123"
    mock_mr.diff_refs = {
        "base_sha": "base_sha_123",
        "start_sha": "start_sha_123",
        "head_sha": "head_sha_123",
    }
    return mock_mr


def test_get_mr_returns_merge_request():
    mock_gl = MagicMock()
    mock_project = MagicMock()
    mock_mr = _make_mock_mr()

    mock_gl.projects.get.return_value = mock_project
    mock_project.mergerequests.get.return_value = mock_mr

    with patch("integrations.gitlab.mr.get_gitlab_client", return_value=mock_gl):
        result = get_mr(1, 2)

    mock_gl.projects.get.assert_called_once_with(1)
    mock_project.mergerequests.get.assert_called_once_with(2)
    assert result is mock_mr


def test_get_mr_files_returns_list():
    mock_mr = _make_mock_mr()
    changes = [{"old_path": "a.py", "new_path": "a.py"}, {"old_path": "b.py", "new_path": "b.py"}]
    mock_mr.changes.return_value = {"changes": changes}

    result = get_mr_files(mock_mr)

    assert result == changes
    mock_mr.changes.assert_called_once()


def test_get_mr_file_content_returns_string():
    mock_gl = MagicMock()
    mock_project = MagicMock()
    mock_mr = _make_mock_mr()

    mock_gl.projects.get.return_value = mock_project
    mock_file = MagicMock()
    mock_file.decode.return_value = b"test content"
    mock_project.files.get.return_value = mock_file

    with patch("integrations.gitlab.mr.get_gitlab_client", return_value=mock_gl):
        result = get_mr_file_content(mock_mr, "test.py")

    mock_project.files.get.assert_called_once_with(file_path="test.py", ref="head_sha_123")
    assert result == "test content"


def test_get_mr_file_content_returns_none_on_error():
    mock_gl = MagicMock()
    mock_project = MagicMock()
    mock_mr = _make_mock_mr()

    mock_gl.projects.get.return_value = mock_project
    mock_project.files.get.side_effect = GitlabGetError("Not found")

    with patch("integrations.gitlab.mr.get_gitlab_client", return_value=mock_gl):
        result = get_mr_file_content(mock_mr, "missing.py")

    assert result is None


def test_get_mr_diff_concatenates_patches():
    mock_mr = _make_mock_mr()
    changes = [
        {"old_path": "a.py", "new_path": "a.py", "diff": "@@ -1,3 +1,4 @@\n+new line\n context"},
        {"old_path": "b.py", "new_path": "b.py", "diff": "@@ -0,0 +1 @@\n+hello"},
    ]
    mock_mr.changes.return_value = {"changes": changes}

    diff = get_mr_diff(mock_mr)
    assert "--- a/a.py" in diff
    assert "+++ b/a.py" in diff
    assert "+new line" in diff
    assert "--- a/b.py" in diff
    assert "+hello" in diff


def test_get_mr_diff_skips_empty_diffs():
    mock_mr = _make_mock_mr()
    changes = [{"old_path": "a.py", "new_path": "a.py", "diff": ""}]
    mock_mr.changes.return_value = {"changes": changes}

    diff = get_mr_diff(mock_mr)
    assert diff == ""


def test_post_issue_comment_calls_notes_create():
    mock_mr = _make_mock_mr()

    post_issue_comment(mock_mr, "test comment")

    mock_mr.notes.create.assert_called_once_with({"body": "test comment"})


def test_post_review_comment_calls_discussions_create():
    mock_mr = _make_mock_mr()

    post_review_comment(mock_mr, "inline comment", "commit_sha", "a.py", 10)

    mock_mr.discussions.create.assert_called_once_with(
        {
            "body": "inline comment",
            "position": {
                "position_type": "text",
                "base_sha": "base_sha_123",
                "start_sha": "start_sha_123",
                "head_sha": "head_sha_123",
                "new_path": "a.py",
                "new_line": 10,
            },
        }
    )


def test_post_findings_as_review_posts_inline_comments():
    mock_mr = _make_mock_mr()
    changes = [
        {
            "old_path": "a.py",
            "new_path": "a.py",
            "diff": "@@ -1,4 +1,5 @@\n context\n-old\n+new line\n context",
        }
    ]
    mock_mr.changes.return_value = {"changes": changes}

    mock_finding = MagicMock()
    mock_finding.file = "a.py"
    mock_finding.line_start = 2
    mock_finding.title = "Test Finding"
    mock_finding.description = "Test Desc"
    mock_finding.fix = MagicMock()
    mock_finding.fix.diff = "fixed code"

    post_findings_as_review(mock_mr, [mock_finding], "head_sha_123")

    mock_mr.discussions.create.assert_called_once()
    called_args = mock_mr.discussions.create.call_args[0][0]
    assert "Test Finding" in called_args["body"]
    assert "```suggestion" in called_args["body"]
    assert called_args["position"]["new_line"] == 2
    assert called_args["position"]["new_path"] == "a.py"
