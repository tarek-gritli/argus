import json
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


def test_review_sse_prints_findings():
    sse_lines = [
        "event: finding",
        f"data: {json.dumps(_FINDING)}",
        "",
        "event: done",
        "data: {}",
        "",
    ]

    mock_stream_resp = MagicMock()
    mock_stream_resp.status_code = 200
    mock_stream_resp.iter_lines = MagicMock(return_value=iter(sse_lines))
    mock_stream_resp.__enter__ = MagicMock(return_value=mock_stream_resp)
    mock_stream_resp.__exit__ = MagicMock(return_value=False)

    mock_client = MagicMock()
    mock_client.post.return_value = MagicMock(
        status_code=202,
        json=lambda: {
            "job_id": "j1",
            "stream_url": "/api/v1/reviews/local/j1/stream",
            "status_url": "/api/v1/reviews/local/j1",
        },
    )
    mock_client.stream.return_value = mock_stream_resp

    with (
        patch("commands.review.load_token", return_value="tok"),
        patch("commands.review.make_client", return_value=mock_client),
        patch("commands.review._get_diff", return_value="+ some code"),
    ):
        app = _make_app()
        result = runner.invoke(app, [])

    assert result.exit_code == 0
    assert "SQL Injection" in result.output


def test_review_sse_failure_falls_back_to_polling():
    mock_client = MagicMock()
    mock_client.post.return_value = MagicMock(
        status_code=202,
        json=lambda: {
            "job_id": "j2",
            "stream_url": "/api/v1/reviews/local/j2/stream",
            "status_url": "/api/v1/reviews/local/j2",
        },
    )
    mock_client.stream.side_effect = Exception("connection refused")
    mock_client.get.side_effect = [
        MagicMock(status_code=202, json=lambda: {"status": "pending"}),
        MagicMock(status_code=200, json=lambda: {"status": "done", "findings": [_FINDING]}),
    ]

    with (
        patch("commands.review.load_token", return_value="tok"),
        patch("commands.review.make_client", return_value=mock_client),
        patch("commands.review._get_diff", return_value="+ some code"),
        patch("commands.review.time.sleep"),
    ):
        app = _make_app()
        result = runner.invoke(app, [])

    assert result.exit_code == 0
    assert "SQL Injection" in result.output


def test_review_clean_result_prints_clean_message():
    sse_lines = ["event: done", "data: {}", ""]

    mock_stream_resp = MagicMock()
    mock_stream_resp.status_code = 200
    mock_stream_resp.iter_lines = MagicMock(return_value=iter(sse_lines))
    mock_stream_resp.__enter__ = MagicMock(return_value=mock_stream_resp)
    mock_stream_resp.__exit__ = MagicMock(return_value=False)

    mock_client = MagicMock()
    mock_client.post.return_value = MagicMock(
        status_code=202,
        json=lambda: {
            "job_id": "j3",
            "stream_url": "/api/v1/reviews/local/j3/stream",
            "status_url": "/api/v1/reviews/local/j3",
        },
    )
    mock_client.stream.return_value = mock_stream_resp

    with (
        patch("commands.review.load_token", return_value="tok"),
        patch("commands.review.make_client", return_value=mock_client),
        patch("commands.review._get_diff", return_value="+ some code"),
    ):
        app = _make_app()
        result = runner.invoke(app, [])

    assert result.exit_code == 0
    assert "No issues" in result.output


def test_review_specific_files_sends_files_in_body():
    sse_lines = ["event: done", "data: {}", ""]

    mock_stream_resp = MagicMock()
    mock_stream_resp.status_code = 200
    mock_stream_resp.iter_lines = MagicMock(return_value=iter(sse_lines))
    mock_stream_resp.__enter__ = MagicMock(return_value=mock_stream_resp)
    mock_stream_resp.__exit__ = MagicMock(return_value=False)

    mock_client = MagicMock()
    mock_client.post.return_value = MagicMock(
        status_code=202,
        json=lambda: {
            "job_id": "j4",
            "stream_url": "/api/v1/reviews/local/j4/stream",
            "status_url": "/api/v1/reviews/local/j4",
        },
    )
    mock_client.stream.return_value = mock_stream_resp

    with (
        patch("commands.review.load_token", return_value="tok"),
        patch("commands.review.make_client", return_value=mock_client),
        patch("commands.review._get_diff", return_value="+ targeted diff"),
    ):
        app = _make_app()
        result = runner.invoke(app, ["src/auth.py", "src/db.py"])

    assert result.exit_code == 0
    call_body = mock_client.post.call_args.kwargs["json"]
    assert call_body["files"] == ["src/auth.py", "src/db.py"]
