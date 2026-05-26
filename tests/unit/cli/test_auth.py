from unittest.mock import patch


def test_save_and_load_token(tmp_path):
    with patch("auth.CREDENTIALS_PATH", tmp_path / "creds.json"):
        from auth import load_token, save_token

        save_token("tok_abc")
        assert load_token() == "tok_abc"


def test_load_token_missing_returns_none(tmp_path):
    with patch("auth.CREDENTIALS_PATH", tmp_path / "creds.json"):
        from auth import load_token

        assert load_token() is None


def test_clear_token(tmp_path):
    creds = tmp_path / "creds.json"
    creds.write_text('{"token":"tok"}')
    with patch("auth.CREDENTIALS_PATH", creds):
        from auth import clear_token, load_token

        clear_token()
        assert load_token() is None
