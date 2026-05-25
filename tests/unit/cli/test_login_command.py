from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

runner = CliRunner()


def _make_app():
    import typer
    from commands.login import login

    app = typer.Typer()
    app.command()(login)
    return app


def test_login_saves_token_on_success():
    mock_client = MagicMock()
    mock_client.post.return_value = MagicMock(
        status_code=200,
        json=lambda: {"session_id": "sid123", "browser_url": "http://localhost:8000/login"},
    )
    pending = MagicMock(status_code=202)
    ready = MagicMock(status_code=200, json=lambda: {"token": "jwt_abc"})
    mock_client.get.side_effect = [pending, ready]

    with (
        patch("commands.login.make_client", return_value=mock_client),
        patch("commands.login.save_token") as mock_save,
        patch("commands.login.webbrowser.open"),
        patch("commands.login.time.sleep"),
    ):
        app = _make_app()
        result = runner.invoke(app, [])

    assert result.exit_code == 0
    mock_save.assert_called_once_with("jwt_abc")
    assert "Logged in" in result.output


def test_login_fails_on_timeout():
    mock_client = MagicMock()
    mock_client.post.return_value = MagicMock(
        status_code=200,
        json=lambda: {"session_id": "sid123", "browser_url": "http://localhost:8000/login"},
    )
    mock_client.get.return_value = MagicMock(status_code=202)

    with (
        patch("commands.login.make_client", return_value=mock_client),
        patch("commands.login.save_token"),
        patch("commands.login.webbrowser.open"),
        patch("commands.login.time.sleep"),
        patch("commands.login._MAX_POLLS", 2),
    ):
        app = _make_app()
        result = runner.invoke(app, [])

    assert result.exit_code == 1
    assert "timed out" in result.output.lower()
