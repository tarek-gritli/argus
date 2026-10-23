from __future__ import annotations

import abc
from dataclasses import dataclass

from integrations.github import (
    PullRequestPayload,
    get_pr,
    get_pr_diff,
    get_pr_file_content,
    get_pr_files,
    update_pr_body,
)
from integrations.github import post_findings_as_review as post_findings_as_review_github
from integrations.github import post_issue_comment as post_issue_comment_github
from integrations.gitlab import (
    MergeRequestPayload,
    get_gitlab_client,
    get_mr,
    get_mr_diff,
    get_mr_file_content,
    get_mr_files,
    update_mr_description,
)
from integrations.gitlab import post_findings_as_review as post_findings_as_review_gitlab
from integrations.gitlab import post_issue_comment as post_issue_comment_gitlab
from shared.crypto import decrypt
from shared.models.org_integration import OrgIntegration
from shared.schemas import FindingSchema
from sqlalchemy import select
from workers.connections import get_session_factory, run_async


@dataclass
class FileChange:
    filename: str
    patch: str


@dataclass
class UnifiedPayload:
    """Provider-neutral view of a PR/MR, passed to every agent."""

    platform: str  # "github" | "gitlab"
    repo_id: str  # GitHub full name, or GitLab path_with_namespace
    pr_id: int  # PR number / MR iid
    head_sha: str
    base_sha: str
    org_id: str = ""
    installation_id: int = 0  # GitHub only
    integration_id: str = ""  # GitLab only (org_integrations.id)
    pr_title: str = ""
    pr_body: str = ""


class VCSProvider(abc.ABC):
    title: str
    body: str
    url: str

    @abc.abstractmethod
    def get_files(self) -> list[FileChange]: ...

    @abc.abstractmethod
    def get_diff(self) -> str: ...

    @abc.abstractmethod
    def get_file_content(self, filename: str) -> str | None: ...

    @abc.abstractmethod
    def post_findings_as_review(self, findings: list[FindingSchema], commit_sha: str) -> None: ...

    @abc.abstractmethod
    def post_issue_comment(self, body: str) -> None: ...

    @abc.abstractmethod
    def update_description(self, body: str) -> None: ...


class GitHubProvider(VCSProvider):
    def __init__(self, payload: dict):
        self.payload = PullRequestPayload(**payload)
        self.pr = get_pr(self.payload.repo_full_name, self.payload.pr_number, self.payload.installation_id)
        self.title = self.pr.title or ""
        self.body = self.pr.body or ""
        self.url = getattr(self.pr, "html_url", None) or (f"https://github.com/{self.payload.repo_full_name}/pull/{self.payload.pr_number}")

    def get_files(self) -> list[FileChange]:
        return [FileChange(filename=f.filename, patch=f.patch or "") for f in get_pr_files(self.pr)]

    def get_diff(self) -> str:
        return get_pr_diff(self.pr)

    def get_file_content(self, filename: str) -> str | None:
        return get_pr_file_content(self.pr, filename)

    def post_findings_as_review(self, findings: list[FindingSchema], commit_sha: str) -> None:
        post_findings_as_review_github(self.pr, findings, commit_sha)

    def post_issue_comment(self, body: str) -> None:
        post_issue_comment_github(self.pr, body)

    def update_description(self, body: str) -> None:
        update_pr_body(self.pr, body)


class GitLabProvider(VCSProvider):
    def __init__(self, payload: dict):
        self.payload = MergeRequestPayload(**payload)
        base_url, token = run_async(_load_credentials(self.payload.org_id, self.payload.integration_id))
        self.mr = get_mr(get_gitlab_client(base_url, token), self.payload.project_id, self.payload.mr_iid)
        self.title = self.mr.title or ""
        self.body = self.mr.description or ""
        self.url = self.mr.web_url

    def get_files(self) -> list[FileChange]:
        return [FileChange(filename=f["new_path"], patch=f.get("diff", "")) for f in get_mr_files(self.mr)]

    def get_diff(self) -> str:
        return get_mr_diff(self.mr)

    def get_file_content(self, filename: str) -> str | None:
        return get_mr_file_content(self.mr, filename)

    def post_findings_as_review(self, findings: list[FindingSchema], commit_sha: str) -> None:
        post_findings_as_review_gitlab(self.mr, findings, commit_sha)

    def post_issue_comment(self, body: str) -> None:
        post_issue_comment_gitlab(self.mr, body)

    def update_description(self, body: str) -> None:
        update_mr_description(self.mr, body)


async def _load_credentials(org_id: str, integration_id: str) -> tuple[str, str]:
    """Instance URL + access token for this org's GitLab integration (never from the task payload)."""
    async with get_session_factory()() as session:
        row = (
            await session.execute(
                select(OrgIntegration).where(
                    OrgIntegration.id == integration_id,
                    OrgIntegration.org_id == org_id,
                    OrgIntegration.kind == "gitlab",
                    OrgIntegration.enabled.is_(True),
                )
            )
        ).scalar_one_or_none()
    if row is None:
        raise ValueError(f"No enabled GitLab integration {integration_id} for org {org_id}")
    return row.config["base_url"], decrypt(row.config["access_token"])


def get_vcs_provider(payload: dict) -> tuple[VCSProvider, UnifiedPayload]:
    platform = payload.get("platform") or ("github" if "repo_full_name" in payload else None)
    if platform == "github":
        provider = GitHubProvider(payload)
        p = provider.payload
        unified = UnifiedPayload(
            platform="github",
            repo_id=p.repo_full_name,
            pr_id=p.pr_number,
            head_sha=p.head_sha,
            base_sha=p.base_sha,
            org_id=p.org_id,
            installation_id=p.installation_id,
        )
    elif platform == "gitlab":
        provider = GitLabProvider(payload)
        p = provider.payload
        unified = UnifiedPayload(
            platform="gitlab",
            repo_id=p.project_path,
            pr_id=p.mr_iid,
            head_sha=p.head_sha,
            base_sha=p.base_sha,
            org_id=p.org_id,
            integration_id=p.integration_id,
        )
    else:
        raise ValueError("Could not determine platform from payload")
    unified.pr_title = provider.title
    unified.pr_body = provider.body
    return provider, unified
