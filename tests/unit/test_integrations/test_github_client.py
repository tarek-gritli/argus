import time
from unittest.mock import MagicMock, patch


def _make_mock_token(token: str = "ghs_test_token", expires_in: int = 3600):
    mock_access_token = MagicMock()
    mock_access_token.token = token
    return mock_access_token


def test_get_installation_token_fetches_fresh_token():
    """First call fetches token from GitHub and caches it."""
    with (
        patch("integrations.github.client._token_cache", {}),
        patch("integrations.github.client.GithubIntegration") as mock_integration_cls,
        patch("integrations.github.client.Auth.AppAuth"),
    ):
        mock_integration = MagicMock()
        mock_integration.get_access_token.return_value = _make_mock_token()
        mock_integration_cls.return_value = mock_integration

        from integrations.github.client import get_installation_token

        token = get_installation_token(42)

        assert token == "ghs_test_token"
        mock_integration.get_access_token.assert_called_once_with(42)


def test_get_installation_token_uses_cache():
    """Subsequent call within TTL returns cached token without hitting GitHub."""
    future_expiry = time.time() + 3000  # well within TTL
    cache = {42: ("ghs_cached_token", future_expiry)}

    with patch("integrations.github.client._token_cache", cache):
        from integrations.github.client import get_installation_token

        token = get_installation_token(42)

        assert token == "ghs_cached_token"


def test_get_installation_token_refreshes_near_expiry():
    """Token within 60s of expiry is refreshed."""
    near_expiry = time.time() + 30  # expires in 30s — inside the 60s refresh window
    cache = {42: ("ghs_expiring_token", near_expiry)}

    with (
        patch("integrations.github.client._token_cache", cache),
        patch("integrations.github.client.GithubIntegration") as mock_integration_cls,
        patch("integrations.github.client.Auth.AppAuth"),
    ):
        mock_integration = MagicMock()
        mock_integration.get_access_token.return_value = _make_mock_token("ghs_new_token")
        mock_integration_cls.return_value = mock_integration

        from integrations.github.client import get_installation_token

        token = get_installation_token(42)

        assert token == "ghs_new_token"
        mock_integration.get_access_token.assert_called_once_with(42)


def test_get_installation_client_returns_github_instance():
    """get_installation_client wraps token into a Github object."""
    future_expiry = time.time() + 3000
    cache = {99: ("ghs_client_token", future_expiry)}

    with (
        patch("integrations.github.client._token_cache", cache),
        patch("integrations.github.client.Github") as mock_github_cls,
    ):
        mock_github = MagicMock()
        mock_github_cls.return_value = mock_github

        from integrations.github.client import get_installation_client

        client = get_installation_client(99)

        mock_github_cls.assert_called_once_with("ghs_client_token")
        assert client is mock_github
