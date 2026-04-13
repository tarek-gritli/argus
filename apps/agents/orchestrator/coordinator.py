import logging

from integrations.github import PullRequestPayload, get_pr, get_pr_files, post_issue_comment
from shared.schemas import FindingSchema
from specialized.security import analyze

logger = logging.getLogger(__name__)


def run(payload: dict) -> None:
    """
    Orchestrate the review pipeline: fetch PR files → analyze → post findings.

    Args:
        payload: dict matching PullRequestPayload schema
    """
    pr_payload = PullRequestPayload(**payload)

    try:
        pr = get_pr(pr_payload.repo_full_name, pr_payload.pr_number, pr_payload.installation_id)
        files = get_pr_files(pr)

        if not files:
            post_issue_comment(pr, "⚠️ No changes detected in this PR.")
            return

        findings = analyze(files, pr_payload)

        comment_body = _format_findings(findings)
        post_issue_comment(pr, comment_body)

    except Exception as e:
        msg = f"Orchestration failed for {pr_payload.repo_full_name}#{pr_payload.pr_number}: {e}"
        logger.error(msg)
        raise


def _format_findings(findings: list[FindingSchema]) -> str:
    """Format findings as a Markdown comment."""
    if not findings:
        return "✅ No security issues found."

    lines = ["## 🔒 Security Review\n"]

    by_severity: dict[str, list[FindingSchema]] = {}
    for finding in findings:
        by_severity.setdefault(finding.severity, []).append(finding)

    for severity in ["critical", "high", "medium", "low", "info"]:
        if severity not in by_severity:
            continue

        lines.append(f"### {severity.upper()}\n")
        for finding in by_severity[severity]:
            lines.append(
                f"**{finding.title}** ({finding.file}:{finding.line_start}-{finding.line_end})\n"
            )
            lines.append(f"{finding.description}\n")
            if finding.suggestion:
                lines.append(f"> Suggestion: {finding.suggestion}\n")
            lines.append("")

    return "\n".join(lines)
