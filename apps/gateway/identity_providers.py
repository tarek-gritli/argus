from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol
from urllib.parse import quote, urlencode

import httpx
from shared.config import Settings

_GITHUB = "https://github.com"
_GITHUB_API = "https://api.github.com"


class ProviderError(Exception):
    """Sign-in with the provider failed; `status` is what the callback should return."""

    def __init__(self, status: int, message: str) -> None:
        self.status = status
        super().__init__(message)


@dataclass(frozen=True)
class Profile:
    provider_user_id: str
    login: str
    name: str | None
    avatar_url: str | None
    primary_email: str | None = None
    verified_emails: frozenset[str] = field(default_factory=frozenset)


class IdentityProvider(Protocol):
    name: str
    label: str
    host: str  # "" for GitHub; the instance URL for GitLab

    def authorize_url(self, state: str) -> str: ...

    async def fetch_profile(self, client: httpx.AsyncClient, code: str) -> Profile: ...


def _json(resp: httpx.Response):
    resp.raise_for_status()
    return resp.json()


class GitHubProvider:
    name = "github"
    label = "GitHub"
    host = ""

    def __init__(self, settings: Settings) -> None:
        self._s = settings

    def authorize_url(self, state: str) -> str:
        q = urlencode({"client_id": self._s.github_client_id, "state": state, "scope": "read:user user:email"}, quote_via=quote)
        return f"{_GITHUB}/login/oauth/authorize?{q}"

    async def fetch_profile(self, client: httpx.AsyncClient, code: str) -> Profile:
        token_resp = await client.post(
            f"{_GITHUB}/login/oauth/access_token",
            data={"client_id": self._s.github_client_id, "client_secret": self._s.github_client_secret, "code": code},
            headers={"Accept": "application/json"},
        )
        access_token = _json(token_resp).get("access_token")
        if not access_token:
            raise ProviderError(400, "GitHub OAuth failed")
        headers = {"Authorization": f"Bearer {access_token}", "Accept": "application/vnd.github+json"}

        user = _json(await client.get(f"{_GITHUB_API}/user", headers=headers))
        if not user.get("id") or not user.get("login"):
            raise ProviderError(502, "Incomplete GitHub user data")

        emails: list[dict] = []
        try:
            emails = _json(await client.get(f"{_GITHUB_API}/user/emails", headers=headers))
        except httpx.HTTPError:
            pass  # sign-in works without emails; only invite acceptance needs them
        verified = frozenset(e["email"].lower() for e in emails if e.get("verified"))
        primary = next((e["email"].lower() for e in emails if e.get("primary") and e.get("verified")), None)
        return Profile(str(user["id"]), user["login"], user.get("name"), user.get("avatar_url"), primary, verified)


class GitLabProvider:
    name = "gitlab"
    label = "GitLab"

    def __init__(self, settings: Settings) -> None:
        self._s = settings
        self.host = settings.gitlab_login_base_url.rstrip("/")

    @property
    def _redirect_uri(self) -> str:
        return f"{self._s.app_base_url}{self._s.api_prefix}/auth/gitlab/callback"

    def authorize_url(self, state: str) -> str:
        q = urlencode(
            {
                "client_id": self._s.gitlab_client_id,
                "redirect_uri": self._redirect_uri,
                "response_type": "code",
                "state": state,
                "scope": "read_user",
            },
            quote_via=quote,
        )
        return f"{self.host}/oauth/authorize?{q}"

    async def fetch_profile(self, client: httpx.AsyncClient, code: str) -> Profile:
        token_resp = await client.post(
            f"{self.host}/oauth/token",
            data={
                "client_id": self._s.gitlab_client_id,
                "client_secret": self._s.gitlab_client_secret,
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": self._redirect_uri,
            },
            headers={"Accept": "application/json"},
        )
        access_token = _json(token_resp).get("access_token")
        if not access_token:
            raise ProviderError(400, "GitLab OAuth failed")
        headers = {"Authorization": f"Bearer {access_token}"}

        user = _json(await client.get(f"{self.host}/api/v4/user", headers=headers))
        if not user.get("id") or not user.get("username"):
            raise ProviderError(502, "Incomplete GitLab user data")

        # GitLab marks an address verified by `confirmed_at`
        confirmed: set[str] = set()
        if user.get("email") and user.get("confirmed_at"):
            confirmed.add(user["email"].lower())
        try:
            for e in _json(await client.get(f"{self.host}/api/v4/user/emails", headers=headers)):
                if e.get("confirmed_at"):
                    confirmed.add(e["email"].lower())
        except httpx.HTTPError:
            pass
        primary = user["email"].lower() if user.get("email") and user["email"].lower() in confirmed else None
        return Profile(str(user["id"]), user["username"], user.get("name"), user.get("avatar_url"), primary, frozenset(confirmed))


def get_providers(settings: Settings) -> dict[str, IdentityProvider]:
    """Sign-in providers that are configured on this deployment."""
    providers: dict[str, IdentityProvider] = {"github": GitHubProvider(settings)}
    if settings.gitlab_client_id and settings.gitlab_client_secret:
        providers["gitlab"] = GitLabProvider(settings)
    return providers
