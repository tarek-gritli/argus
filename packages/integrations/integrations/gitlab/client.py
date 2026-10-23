from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlsplit

import gitlab
from shared.config import get_settings

DEFAULT_BASE_URL = "https://gitlab.com"


class InvalidGitLabURL(ValueError):
    pass


def normalize_base_url(url: str) -> str:
    """Return a canonical https://host[:port][/prefix] URL or raise InvalidGitLabURL."""
    parts = urlsplit((url or "").strip())
    allowed = {"https"} | ({"http"} if get_settings().env == "development" else set())
    if parts.scheme not in allowed or not parts.hostname:
        raise InvalidGitLabURL("GitLab URL must be an https:// URL")
    if parts.username or parts.password or parts.query or parts.fragment:
        raise InvalidGitLabURL("GitLab URL must not contain credentials, query or fragment")
    return f"{parts.scheme}://{parts.netloc}{parts.path.rstrip('/')}"


def assert_public_host(base_url: str) -> None:
    """Refuse hosts that resolve to internal addresses — the URL is tenant-supplied (SSRF)."""
    if get_settings().gitlab_allow_private_hosts:
        return
    host = urlsplit(base_url).hostname or ""
    try:
        addrs = {info[4][0] for info in socket.getaddrinfo(host, None)}
    except socket.gaierror as exc:
        raise InvalidGitLabURL(f"Cannot resolve GitLab host {host!r}") from exc
    for addr in addrs:
        ip = ipaddress.ip_address(addr)
        if not ip.is_global:
            raise InvalidGitLabURL("GitLab host resolves to a non-public address")


def get_gitlab_client(base_url: str, token: str) -> gitlab.Gitlab:
    """Authenticated client for one GitLab instance (gitlab.com or self-hosted)."""
    base_url = normalize_base_url(base_url)
    assert_public_host(base_url)
    return gitlab.Gitlab(url=base_url, private_token=token, timeout=20)
