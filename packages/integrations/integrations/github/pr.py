from github import Github
from github.File import File
from github.PullRequest import PullRequest

from .client import get_installation_client


def get_pr(repo_full_name: str, pr_number: int, installation_id: int) -> PullRequest:
    gh: Github = get_installation_client(installation_id)
    repo = gh.get_repo(repo_full_name)
    return repo.get_pull(pr_number)


def get_pr_files(pr: PullRequest) -> list[File]:
    """Return changed files for a PR."""
    return list(pr.get_files())


def post_issue_comment(pr: PullRequest, body: str) -> None:
    """Post a comment on a PR."""
    pr.create_issue_comment(body)


def post_review_comment(
    pr: PullRequest,
    body: str,
    commit_sha: str,
    path: str,
    line: int,
) -> None:
    """Post an inline review comment on a specific file line."""
    commit = pr.head.repo.get_commit(commit_sha)
    pr.create_review_comment(
        body=body,
        commit=commit,
        path=path,
        line=line,
        side="RIGHT",
    )
