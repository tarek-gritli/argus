from unittest.mock import MagicMock, patch

import pytest
from integrations.gitlab.client import InvalidGitLabURL, assert_public_host, get_gitlab_client, normalize_base_url


def _settings(env="production", allow_private=False):
    s = MagicMock()
    s.env = env
    s.gitlab_allow_private_hosts = allow_private
    return s


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("https://gitlab.com", "https://gitlab.com"),
        ("  https://git.corp.io/  ", "https://git.corp.io"),
        ("https://corp.io:8443/gitlab/", "https://corp.io:8443/gitlab"),
    ],
)
def test_normalize_base_url_accepts_https(raw, expected):
    with patch("integrations.gitlab.client.get_settings", return_value=_settings()):
        assert normalize_base_url(raw) == expected


@pytest.mark.parametrize(
    "raw",
    ["http://gitlab.com", "ftp://gitlab.com", "gitlab.com", "", "https://u:p@gitlab.com", "https://gitlab.com/?a=1"],
)
def test_normalize_base_url_rejects_unsafe(raw):
    with patch("integrations.gitlab.client.get_settings", return_value=_settings()), pytest.raises(InvalidGitLabURL):
        normalize_base_url(raw)


def test_normalize_base_url_allows_http_in_development():
    with patch("integrations.gitlab.client.get_settings", return_value=_settings(env="development")):
        assert normalize_base_url("http://localhost:8080") == "http://localhost:8080"


@pytest.mark.parametrize("addr", ["127.0.0.1", "10.0.0.5", "169.254.169.254", "192.168.1.1", "::1"])
def test_assert_public_host_blocks_internal_addresses(addr):
    with (
        patch("integrations.gitlab.client.get_settings", return_value=_settings()),
        patch("integrations.gitlab.client.socket.getaddrinfo", return_value=[(0, 0, 0, "", (addr, 0))]),
        pytest.raises(InvalidGitLabURL),
    ):
        assert_public_host("https://evil.example")


def test_assert_public_host_allows_public_and_private_when_enabled():
    with (
        patch("integrations.gitlab.client.get_settings", return_value=_settings()),
        patch("integrations.gitlab.client.socket.getaddrinfo", return_value=[(0, 0, 0, "", ("8.8.8.8", 0))]),
    ):
        assert_public_host("https://gitlab.example")
    with (
        patch("integrations.gitlab.client.get_settings", return_value=_settings(allow_private=True)),
        patch("integrations.gitlab.client.socket.getaddrinfo", return_value=[(0, 0, 0, "", ("10.0.0.5", 0))]),
    ):
        assert_public_host("https://gitlab.internal")


def test_get_gitlab_client_uses_given_instance_and_token():
    with (
        patch("integrations.gitlab.client.get_settings", return_value=_settings()),
        patch("integrations.gitlab.client.assert_public_host"),
        patch("integrations.gitlab.client.gitlab.Gitlab") as mock_gitlab_cls,
    ):
        client = get_gitlab_client("https://git.corp.io/", "glpat-test")

    mock_gitlab_cls.assert_called_once_with(url="https://git.corp.io", private_token="glpat-test", timeout=20)
    assert client is mock_gitlab_cls.return_value
