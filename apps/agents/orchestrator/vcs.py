import abc
import logging
from dataclasses import dataclass

import gitlab
from integrations.github import (
    PullRequestPayload,
    get_pr,
    get_pr_diff,
    get_pr_file_content,
    get_pr_files,
)
from integrations.github import (
    post_findings_as_review as post_findings_as_review_github,
)
from integrations.github import (
    post_issue_comment as post_issue_comment_github,
)
from integrations.gitlab import (
    MergeRequestPayload,
    get_mr,
    get_mr_diff,
    get_mr_file_content,
    get_mr_files,
)
from integrations.gitlab import (
    post_findings_as_review as post_findings_as_review_gitlab,
)
from integrations.gitlab import (
    post_issue_comment as post_issue_comment_gitlab,
)
from shared.schemas import FindingSchema


@dataclass
class FileChange:
    filename: str
    patch: str


@dataclass
class UnifiedPayload:
    platform: str
    repo_id: str
    pr_id: int
    head_sha: str
    base_sha: str


class VCSProvider(abc.ABC):
    @abc.abstractmethod
    def get_files(self) -> list[FileChange]:
        pass

    @abc.abstractmethod
    def get_diff(self) -> str:
        pass

    @abc.abstractmethod
    def get_file_content(self, filename: str) -> str | None:
        pass

    @abc.abstractmethod
    def post_findings_as_review(self, findings: list[FindingSchema], commit_sha: str) -> None:
        pass

    @abc.abstractmethod
    def post_issue_comment(self, body: str) -> None:
        pass


class GitHubProvider(VCSProvider):
    def __init__(self, payload: dict):
        self.payload = PullRequestPayload(**payload)
        self.pr = get_pr(self.payload.repo_full_name, self.payload.pr_number, self.payload.installation_id)

    def get_files(self) -> list[FileChange]:
        files = get_pr_files(self.pr)
        return [FileChange(filename=f.filename, patch=f.patch or "") for f in files]

    def get_diff(self) -> str:
        return get_pr_diff(self.pr)

    def get_file_content(self, filename: str) -> str | None:
        return get_pr_file_content(self.pr, filename)

    def post_findings_as_review(self, findings: list[FindingSchema], commit_sha: str) -> None:
        post_findings_as_review_github(self.pr, findings, commit_sha)

    def post_issue_comment(self, body: str) -> None:
        post_issue_comment_github(self.pr, body)


class GitLabProvider(VCSProvider):
    def __init__(self, payload: dict):
        self.payload = MergeRequestPayload(**payload)
        try:
            self.mr = get_mr(self.payload.project_id, self.payload.mr_iid)
        except gitlab.exceptions.GitlabGetError as e:
            logging.getLogger(__name__).error(
                "Failed to resolve GitLab MR: project=%s mr_iid=%s error=%s",
                self.payload.project_id,
                self.payload.mr_iid,
                e,
            )
            # Raise a ValueError so upstream orchestration can handle it gracefully
            raise ValueError(f"Could not resolve GitLab MR for project={self.payload.project_id} mr_iid={self.payload.mr_iid}") from e

    def get_files(self) -> list[FileChange]:
        files = get_mr_files(self.mr)
        return [FileChange(filename=f["new_path"], patch=f.get("diff", "")) for f in files]

    def get_diff(self) -> str:
        return get_mr_diff(self.mr)

    def get_file_content(self, filename: str) -> str | None:
        return get_mr_file_content(self.mr, filename)

    def post_findings_as_review(self, findings: list[FindingSchema], commit_sha: str) -> None:
        post_findings_as_review_gitlab(self.mr, findings, commit_sha)

    def post_issue_comment(self, body: str) -> None:
        post_issue_comment_gitlab(self.mr, body)


def get_vcs_provider(payload: dict) -> tuple[VCSProvider, UnifiedPayload]:
    platform = payload.get("platform")
    if platform == "github":
        provider = GitHubProvider(payload)
        unified = UnifiedPayload(
            platform="github",
            repo_id=provider.payload.repo_full_name,
            pr_id=provider.payload.pr_number,
            head_sha=provider.payload.head_sha,
            base_sha=provider.payload.base_sha,
        )
        return provider, unified
    elif platform == "gitlab":
        provider = GitLabProvider(payload)
        unified = UnifiedPayload(
            platform="gitlab",
            repo_id=str(provider.payload.project_id),
            pr_id=provider.payload.mr_iid,
            head_sha=provider.payload.head_sha,
            base_sha=provider.payload.base_sha,
        )
        return provider, unified
    else:
        # Fallback for old payloads missing platform key
        if "repo_full_name" in payload:
            provider = GitHubProvider(payload)
            unified = UnifiedPayload(
                platform="github",
                repo_id=provider.payload.repo_full_name,
                pr_id=provider.payload.pr_number,
                head_sha=provider.payload.head_sha,
                base_sha=provider.payload.base_sha,
            )
            return provider, unified
        else:
            raise ValueError("Could not determine platform from payload")
