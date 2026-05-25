import re
from collections.abc import Iterable

from github import Github
from github.File import File
from github.PullRequest import PullRequest

from .client import get_installation_client

_IGNORED_PATH_PREFIXES = (
    "node_modules/",
    "vendor/",
    "dist/",
    "build/",
    ".next/",
    ".turbo/",
    ".cache/",
    "coverage/",
    "__pycache__/",
    ".venv/",
)

_IGNORED_PATH_SEGMENTS = frozenset(
    {
        "node_modules",
        "vendor",
        "dist",
        "build",
        ".next",
        ".turbo",
        ".cache",
        "coverage",
        "__pycache__",
        ".venv",
    }
)

_IGNORED_SUFFIXES = (
    ".min.js",
    ".min.css",
    ".map",
)


def _normalise_path(filename: str) -> str:
    return filename.replace("\\", "/")


def _is_reviewable_file(filename: str, patch: str | None = None) -> bool:
    path = _normalise_path(filename)

    if any(path.startswith(prefix) for prefix in _IGNORED_PATH_PREFIXES):
        return False

    if any(segment in _IGNORED_PATH_SEGMENTS for segment in path.split("/")):
        return False

    if path.endswith(_IGNORED_SUFFIXES):
        return False

    if not patch:
        return False

    return True


def _reviewable_files(files: Iterable[File]) -> list[File]:
    return [f for f in files if _is_reviewable_file(f.filename, getattr(f, "patch", None))]


def get_pr(repo_full_name: str, pr_number: int, installation_id: int) -> PullRequest:
    gh: Github = get_installation_client(installation_id)
    repo = gh.get_repo(repo_full_name)
    return repo.get_pull(pr_number)


def get_pr_files(pr: PullRequest) -> list[File]:
    """Return changed files for a PR."""
    return _reviewable_files(pr.get_files())


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


def get_pr_diff(pr: PullRequest, files: Iterable[File] | None = None) -> str:
    """Return the full unified diff for a PR as a single string."""
    parts: list[str] = []
    for f in _reviewable_files(files or pr.get_files()):
        if not f.patch:
            continue
        parts.append(f"--- a/{f.filename}")
        parts.append(f"+++ b/{f.filename}")
        parts.append(f.patch)
    return "\n".join(parts)


def post_issue_comment(pr: PullRequest, body: str) -> None:
    """Post a comment on a PR."""
    pr.create_issue_comment(body)


def update_pr_body(pr: PullRequest, body: str) -> None:
    """Update the PR description body."""
    if not body or not body.strip():
        return
    pr.edit(body=body)


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


def post_findings_as_review(
    pr: PullRequest,
    findings: list,
    commit_sha: str,
) -> None:
    """
    Post findings as a single GitHub review with inline comments.

    Findings with a fix are posted with a ```suggestion``` block so the
    author can accept the patch with one click. Findings without a fix are
    posted as plain inline comments.

    Only findings whose line numbers fall within the PR diff are posted
    inline — GitHub rejects review comments on lines not present in the diff.
    Findings outside the diff are silently skipped (they still appear in the
    summary issue comment posted by the coordinator).
    """
    if not findings:
        return

    commit = pr.head.repo.get_commit(commit_sha)

    # Build set of (filename, line) pairs that are part of this PR's diff
    # so we only post inline comments on lines GitHub will accept.
    diff_lines: set[tuple[str, int]] = set()
    for f in pr.get_files():
        if not f.patch:
            continue
        current_line = 0
        for patch_line in f.patch.splitlines():
            if patch_line.startswith("@@"):
                # Extract the starting line number from the hunk header
                # e.g. @@ -1,4 +3,8 @@ → new file starts at line 3
                m = re.search(r"\+(\d+)", patch_line)
                if m:
                    current_line = int(m.group(1)) - 1
            elif not patch_line.startswith("-"):
                current_line += 1
                diff_lines.add((f.filename, current_line))

    comments = []
    for finding in findings:
        if (finding.file, finding.line_start) not in diff_lines:
            continue

        if finding.fix and finding.fix.diff:
            body = f"**{finding.title}**\n{finding.description}\n\n```suggestion\n{finding.fix.diff}\n```"
        else:
            body = f"**{finding.title}**\n{finding.description}"
            if finding.suggestion:
                body += f"\n\n> {finding.suggestion}"

        comments.append(
            {
                "path": finding.file,
                "line": finding.line_start,
                "side": "RIGHT",
                "body": body,
            }
        )

    if not comments:
        return

    pr.create_review(
        commit=commit,
        body="",
        event="COMMENT",
        comments=comments,
    )


_CODE_EXTENSIONS = {
    ".py",
    ".js",
    ".ts",
    ".tsx",
    ".jsx",
    ".go",
    ".rs",
    ".java",
    ".rb",
    ".cpp",
    ".cc",
    ".cxx",
    ".c",
    ".h",
    ".cs",
    ".kt",
    ".kts",
    ".php",
}


def get_repo_files(repo_full_name: str, installation_id: int, ref: str = "main") -> list[dict]:
    """Fetch all indexable source files from a repo at a given ref."""
    client = get_installation_client(installation_id)
    repo = client.get_repo(repo_full_name)
    tree = repo.get_git_tree(ref, recursive=True)
    files = []
    for item in tree.tree:
        if item.type != "blob":
            continue
        ext = "." + item.path.rsplit(".", 1)[-1] if "." in item.path else ""
        if ext not in _CODE_EXTENSIONS:
            continue
        try:
            blob = repo.get_contents(item.path, ref=ref)
            if isinstance(blob, list):
                continue
            files.append(
                {
                    "filename": item.path,
                    "content": blob.decoded_content.decode("utf-8", errors="replace"),
                }
            )
        except Exception:
            continue
    return files
