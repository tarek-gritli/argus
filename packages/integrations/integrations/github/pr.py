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


def get_pr_file_content(pr: PullRequest, filename: str) -> str | None:
    """Fetch the full content of a file at the PR's head commit."""
    try:
        content_file = pr.head.repo.get_contents(filename, ref=pr.head.sha)
        # In PyGithub, if it's a single file, it returns a ContentFile.
        # If it's a list (which happens if it's a dir, but we pass a filename), it returns list.
        if isinstance(content_file, list):
            return None
        return content_file.decoded_content.decode("utf-8")
    except Exception:
        return None


def get_pr_diff(pr: PullRequest) -> str:
    """Return the full unified diff for a PR as a single string."""
    parts: list[str] = []
    for f in pr.get_files():
        if not f.patch:
            continue
        parts.append(f"--- a/{f.filename}")
        parts.append(f"+++ b/{f.filename}")
        parts.append(f.patch)
    return "\n".join(parts)


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
