import logging

from fix_engine.pipeline import run_fix_pipeline
from integrations.github import PullRequestPayload, get_pr, get_pr_diff, get_pr_file_content, get_pr_files, post_findings_as_review, post_issue_comment
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

        # Build the files_content mapping for the fix engine
        files_content: dict[str, str] = {}
        for finding in findings:
            if finding.file not in files_content:
                content = get_pr_file_content(pr, finding.file)
                if content is not None:
                    files_content[finding.file] = content

        # Run the fix engine to attempt to generate patches
        findings = run_fix_pipeline(findings, files_content)

        # Post inline review suggestions for findings with fixes; summary comment for all findings
        post_findings_as_review(pr, findings, pr_payload.head_sha)
        post_issue_comment(pr, _format_findings(findings))

    except Exception:
        logger.exception("Orchestration failed")
        raise


def _format_findings(findings: list[FindingSchema]) -> str:
    if not findings:
        return "✅ No issues found across all review agents."

    by_agent: dict[str, dict[str, list[FindingSchema]]] = {}
    for f in findings:
        by_agent.setdefault(f.agent, {}).setdefault(f.severity, []).append(f)

    lines = ["## Argus Code Review\n"]

    _AGENT_ORDER = ("security", "quality", "testing")
    ordered = [k for k in _AGENT_ORDER if k in by_agent]
    ordered += [k for k in by_agent if k not in _AGENT_ORDER]

    for agent_key in ordered:
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
                if finding.fix:
                    lines.append(f"<details>\n<summary>💡 Suggested Fix: <i>{finding.fix.description}</i></summary>\n")
                    lines.append(f"```\n{finding.fix.diff}\n```\n</details>\n")
                lines.append("")

    return "\n".join(lines)
