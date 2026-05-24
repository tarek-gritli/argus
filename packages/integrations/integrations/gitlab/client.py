import gitlab
from shared.config import get_settings


def get_gitlab_client() -> gitlab.Gitlab:
    """Get an authenticated GitLab client."""
    settings = get_settings()
    # Note: If self-hosted, URL should be a config variable.
    return gitlab.Gitlab(
        url="https://gitlab.com",
        private_token=settings.gitlab_access_token,
    )
