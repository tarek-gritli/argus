import base64
import time

from github import Auth, Github, GithubIntegration
from shared.config import get_settings

_token_cache: dict[int, tuple[str, float]] = {}


def get_installation_token(installation_id: int) -> str:
    """Fetch or cache GitHub App installation access token."""
    now = time.time()

    if installation_id in _token_cache:
        token, expires_at = _token_cache[installation_id]
        if now < expires_at - 60:
            return token

    settings = get_settings()
    app_id = int(settings.github_app_id)
    private_key = base64.b64decode(settings.github_private_key_b64).decode()

    auth = Auth.AppAuth(app_id, private_key)
    integration = GithubIntegration(auth=auth)
    access_token = integration.get_access_token(installation_id)

    expires_at = now + 3600
    _token_cache[installation_id] = (access_token.token, expires_at)

    return access_token.token


def get_installation_client(installation_id: int) -> Github:
    token = get_installation_token(installation_id)
    return Github(token)
