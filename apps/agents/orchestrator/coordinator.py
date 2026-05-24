import logging

from fix_engine.pipeline import run_fix_pipeline
from shared.schemas import FindingSchema

from .graph import run_review
from .vcs import get_vcs_provider

logger = logging.getLogger(__name__)

_AGENT_LABELS = {
    "security": "Security",
    "quality": "Quality",
    "testing": "Testing",
}

_SEVERITY_ORDER = ["critical", "high", "medium", "low", "info"]


def run(payload: dict) -> None:
    try:
        provider, unified_payload = get_vcs_provider(payload)
        files = provider.get_files()

        if not files:
            provider.post_issue_comment("⚠️ No changes detected in this PR.")
            return

        diff = provider.get_diff()
        findings = run_review(files=files, diff=diff, pr_payload=unified_payload)

        # Build the files_content mapping for the fix engine
        files_content: dict[str, str] = {}
        for finding in findings:
            if finding.file not in files_content:
                content = provider.get_file_content(finding.file)
                if content is not None:
                    files_content[finding.file] = content

        # Run the fix engine to attempt to generate patches
        findings = run_fix_pipeline(findings, files_content)

        # Post inline review suggestions for findings with fixes; summary comment for all findings
        provider.post_findings_as_review(findings, unified_payload.head_sha)
        provider.post_issue_comment(_format_findings(findings))

    except ValueError as e:
        # Expected failures (e.g. could not resolve MR/project). Log and stop orchestration.
        logger.error("Orchestration aborted: %s", e)
        return
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
