from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

runner = CliRunner()


def _make_app():
    import typer
    from commands.review import review

    app = typer.Typer()
    app.command()(review)
    return app


_FINDING = {
    "agent": "security",
    "severity": "high",
    "file": "src/auth.py",
    "line_start": 10,
    "line_end": 15,
    "title": "SQL Injection",
    "description": "User input not sanitized.",
    "suggestion": "Use parameterized queries.",
    "confidence": 0.95,
    "fix": None,
}


def test_review_whole_diff_prints_findings():
    with (
        patch("commands.review.load_token", return_value="tok"),
        patch("commands.review.make_client") as mock_make_client,
        patch("commands.review._get_diff", return_value="+ some code"),
    ):
        mock_client = MagicMock()
        mock_client.post.return_value = MagicMock(status_code=200, json=lambda: {"findings": [_FINDING]})
        mock_make_client.return_value = mock_client

        app = _make_app()
        result = runner.invoke(app, [])

    assert result.exit_code == 0
    assert "SQL Injection" in result.output
    assert "HIGH" in result.output.upper()


def test_review_specific_files():
    with (
        patch("commands.review.load_token", return_value="tok"),
        patch("commands.review.make_client") as mock_make_client,
        patch("commands.review._get_diff", return_value="+ targeted diff"),
    ):
        mock_client = MagicMock()
        mock_client.post.return_value = MagicMock(status_code=200, json=lambda: {"findings": [_FINDING]})
        mock_make_client.return_value = mock_client

        app = _make_app()
        result = runner.invoke(app, ["src/auth.py", "src/db.py"])

    assert result.exit_code == 0
    call_body = mock_client.post.call_args.kwargs["json"]
    assert call_body["files"] == ["src/auth.py", "src/db.py"]


def test_review_not_logged_in_exits_with_error():
    with patch("commands.review.load_token", return_value=None):
        app = _make_app()
        result = runner.invoke(app, [])

    assert result.exit_code == 1
    assert "argus login" in result.output.lower()


def test_review_no_diff_exits_cleanly():
    with (
        patch("commands.review.load_token", return_value="tok"),
        patch("commands.review._get_diff", return_value=""),
    ):
        app = _make_app()
        result = runner.invoke(app, [])

    assert result.exit_code == 0
    assert "No changes" in result.output


def test_review_clean_result_prints_clean_message():
    with (
        patch("commands.review.load_token", return_value="tok"),
        patch("commands.review.make_client") as mock_make_client,
        patch("commands.review._get_diff", return_value="+ code"),
    ):
        mock_client = MagicMock()
        mock_client.post.return_value = MagicMock(status_code=200, json=lambda: {"findings": []})
        mock_make_client.return_value = mock_client

        app = _make_app()
        result = runner.invoke(app, [])

    assert result.exit_code == 0
    assert "No issues" in result.output
