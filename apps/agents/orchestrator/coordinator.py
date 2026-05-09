import logging

from integrations.github import PullRequestPayload, get_pr, get_pr_diff, get_pr_files, post_issue_comment
from shared.schemas import FindingSchema

from .graph import run_review

logger = logging.getLogger(__name__)

_AGENT_LABELS = {
    "security": "Security",
    "quality": "Quality",
    "testing": "Testing",
}

_SEVERITY_ORDER = ["critical", "high", "medium", "low", "info"]


def run(payload: dict) -> None:
    try:
        pr_payload = PullRequestPayload(**payload)
        pr = get_pr(pr_payload.repo_full_name, pr_payload.pr_number, pr_payload.installation_id)
        files = get_pr_files(pr)

        if not files:
            post_issue_comment(pr, "⚠️ No changes detected in this PR.")
            return

        diff = get_pr_diff(pr)
        findings = run_review(files=files, diff=diff, pr_payload=pr_payload)
        post_issue_comment(pr, _format_findings(findings))

    except Exception as e:
        logger.error("Orchestration failed: %s", e)
        raise


def _format_findings(findings: list[FindingSchema]) -> str:
    if not findings:
        return "✅ No issues found across all review agents."

    by_agent: dict[str, dict[str, list[FindingSchema]]] = {}
    for f in findings:
        by_agent.setdefault(f.agent, {}).setdefault(f.severity, []).append(f)

    lines = ["## Argus Code Review\n"]

    for agent_key in ("security", "quality", "testing"):
        if agent_key not in by_agent:
            continue
        label = _AGENT_LABELS.get(agent_key, agent_key.title())
        lines.append(f"### {label} Review\n")
        for severity in _SEVERITY_ORDER:
            bucket = by_agent[agent_key].get(severity, [])
            if not bucket:
                continue
            lines.append(f"#### {severity.upper()}\n")
            for finding in bucket:
                lines.append(f"**{finding.title}** (`{finding.file}:{finding.line_start}-{finding.line_end}`)\n")
                lines.append(f"{finding.description}\n")
                if finding.suggestion:
                    lines.append(f"> Suggestion: {finding.suggestion}\n")
                lines.append("")

    return "\n".join(lines)
