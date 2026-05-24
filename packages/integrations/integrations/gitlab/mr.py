import logging
import re
import urllib.parse
from typing import Any

import gitlab
from gitlab.v4.objects import ProjectMergeRequest

from .client import get_gitlab_client

logger = logging.getLogger(__name__)


def get_mr(project_id: int | str, mr_iid: int) -> ProjectMergeRequest:
    """Resolve a project and return its Merge Request object.

    Accepts either a numeric project_id or a namespace/path string. If the
    initial numeric lookup returns 404, we attempt a path-based lookup and a
    best-effort search before raising the original error with extra context.
    """
    gl = get_gitlab_client()

    # First attempt: direct lookup (numeric id or canonical path)
    try:
        project = gl.projects.get(project_id)
        return project.mergerequests.get(mr_iid)
    except gitlab.exceptions.GitlabGetError as initial_exc:
        logger.debug("Initial lookup for project %s failed: %s", project_id, initial_exc)

    # If project_id is a path-like string, try URL-encoding and lookup
    if isinstance(project_id, str) and "/" in project_id:
        try:
            encoded = urllib.parse.quote_plus(project_id)
            project = gl.projects.get(encoded)
            return project.mergerequests.get(mr_iid)
        except gitlab.exceptions.GitlabGetError:
            logger.debug("Path lookup with encoded project path failed: %s", project_id)

    # As a last resort, try searching projects by name (best-effort)
    try:
        search_term = str(project_id)
        projects = gl.projects.list(search=search_term, as_list=False)
        # projects is a paginated list; convert to list and try the first sensible match
        candidates = list(projects)
        if candidates:
            project = candidates[0]
            logger.debug("Found candidate project via search: %s (id=%s)", project.path_with_namespace, project.id)
            return project.mergerequests.get(mr_iid)
    except Exception as search_exc:  # broad catch because search can vary by client/server
        logger.debug("Project search attempt failed for %s: %s", project_id, search_exc)

    # Nothing worked; raise a clear error with context
    msg = f"Could not find GitLab project '{project_id}' when looking up MR iid={mr_iid}"
    logger.error(msg)
    raise gitlab.exceptions.GitlabGetError(msg)


def get_mr_files(mr: ProjectMergeRequest) -> list[dict[str, Any]]:
    """Return changed files for a MR."""
    return mr.changes()["changes"]


def get_mr_file_content(mr: ProjectMergeRequest, filename: str) -> str | None:
    """Fetch the full content of a file at the MR's head commit."""
    gl = get_gitlab_client()
    project = gl.projects.get(mr.project_id)
    try:
        f = project.files.get(file_path=filename, ref=mr.sha)
        return f.decode().decode("utf-8")
    except gitlab.exceptions.GitlabGetError:
        return None


def get_mr_diff(mr: ProjectMergeRequest) -> str:
    """Return the full unified diff for an MR as a single string."""
    parts: list[str] = []
    for change in mr.changes()["changes"]:
        diff = change.get("diff", "")
        if not diff:
            continue
        parts.append(f"--- a/{change['old_path']}")
        parts.append(f"+++ b/{change['new_path']}")
        parts.append(diff)
    return "\n".join(parts)


def post_issue_comment(mr: ProjectMergeRequest, body: str) -> None:
    """Post a comment on an MR."""
    mr.notes.create({"body": body})


def post_review_comment(
    mr: ProjectMergeRequest,
    body: str,
    commit_sha: str,
    path: str,
    line: int,
) -> None:
    """Post an inline review comment on a specific file line."""
    diff_refs = mr.diff_refs
    mr.discussions.create(
        {
            "body": body,
            "position": {
                "position_type": "text",
                "base_sha": diff_refs["base_sha"],
                "start_sha": diff_refs["start_sha"],
                "head_sha": diff_refs["head_sha"],
                "new_path": path,
                "new_line": line,
            },
        }
    )


def post_findings_as_review(
    mr: ProjectMergeRequest,
    findings: list,
    commit_sha: str,
) -> None:
    """
    Post findings as inline comments via GitLab discussions.
    """
    if not findings:
        return

    diff_refs = mr.diff_refs

    # Build set of (filename, line) pairs that are part of this MR's diff
    diff_lines: set[tuple[str, int]] = set()
    for change in mr.changes()["changes"]:
        diff = change.get("diff", "")
        if not diff:
            continue
        current_line = 0
        for patch_line in diff.splitlines():
            if patch_line.startswith("@@"):
                m = re.search(r"\+(\d+)", patch_line)
                if m:
                    current_line = int(m.group(1)) - 1
            elif not patch_line.startswith("-"):
                current_line += 1
                diff_lines.add((change["new_path"], current_line))

    for finding in findings:
        if (finding.file, finding.line_start) not in diff_lines:
            continue

        if finding.fix and finding.fix.diff:
            body = f"**{finding.title}**\n{finding.description}\n\n```suggestion\n{finding.fix.diff}\n```"
        else:
            body = f"**{finding.title}**\n{finding.description}"
            if finding.suggestion:
                body += f"\n\n> {finding.suggestion}"

        mr.discussions.create(
            {
                "body": body,
                "position": {
                    "position_type": "text",
                    "base_sha": diff_refs["base_sha"],
                    "start_sha": diff_refs["start_sha"],
                    "head_sha": diff_refs["head_sha"],
                    "new_path": finding.file,
                    "new_line": finding.line_start,
                },
            }
        )
