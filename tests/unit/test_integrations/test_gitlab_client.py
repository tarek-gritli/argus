from unittest.mock import MagicMock, patch

from integrations.gitlab.client import get_gitlab_client


def test_get_gitlab_client():
    """get_gitlab_client returns an authenticated gitlab.Gitlab instance."""
    mock_settings = MagicMock()
    mock_settings.gitlab_access_token = "glpat-test12345"

    with (
        patch("integrations.gitlab.client.get_settings", return_value=mock_settings),
        patch("integrations.gitlab.client.gitlab.Gitlab") as mock_gitlab_cls,
    ):
        mock_gl_instance = MagicMock()
        mock_gitlab_cls.return_value = mock_gl_instance

        client = get_gitlab_client()

        mock_gitlab_cls.assert_called_once_with(
            url="https://gitlab.com",
            private_token="glpat-test12345",
        )
        assert client is mock_gl_instance
