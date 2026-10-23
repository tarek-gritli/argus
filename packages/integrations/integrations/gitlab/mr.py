import logging
import re
from typing import Any, cast

import gitlab
from gitlab.exceptions import GitlabGetError
from gitlab.v4.objects.merge_requests import ProjectMergeRequest

logger = logging.getLogger(__name__)


def _changes(mr: ProjectMergeRequest) -> list[dict[str, Any]]:
    # python-gitlab types changes() as dict | Response; the API always returns the JSON dict
    return cast(dict, mr.changes())["changes"]


def get_mr(gl: gitlab.Gitlab, project_id: int, mr_iid: int) -> ProjectMergeRequest:
    """Fetch an MR by exact numeric project id.

    No path/search fallbacks: resolving a "best match" project could review (and post
    comments on) the wrong tenant's code. Fails closed with GitlabGetError.
    """
    project = gl.projects.get(project_id)
    if project.id != project_id:
        raise ValueError(f"GitLab returned project {project.id}, expected {project_id}")
    return project.mergerequests.get(mr_iid)


def get_mr_files(mr: ProjectMergeRequest) -> list[dict[str, Any]]:
    """Return changed files for a MR."""
    return _changes(mr)


def get_mr_file_content(mr: ProjectMergeRequest, filename: str) -> str | None:
    """Fetch the full content of a file at the MR's head commit."""
    project = mr.manager.gitlab.projects.get(mr.project_id)
    try:
        f = project.files.get(file_path=filename, ref=mr.sha)
        return f.decode().decode("utf-8")
    except GitlabGetError:
        return None


def get_mr_diff(mr: ProjectMergeRequest) -> str:
    """Return the full unified diff for an MR as a single string."""
    parts: list[str] = []
    for change in _changes(mr):
        diff = change.get("diff", "")
        if not diff:
            continue
        parts.append(f"--- a/{change['old_path']}")
        parts.append(f"+++ b/{change['new_path']}")
        parts.append(diff)
    return "\n".join(parts)


def update_mr_description(mr: ProjectMergeRequest, body: str) -> None:
    mr.description = body
    mr.save()


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
    for change in _changes(mr):
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
