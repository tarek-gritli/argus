from __future__ import annotations

import re

from shared.schemas import FindingSchema

_AGENT_LABELS = {
    "security": "Security",
    "quality": "Quality",
    "testing": "Testing",
    "documentation": "Documentation",
    "ticket_compliance": "Ticket Compliance",
}

_SEVERITY_ORDER = ["critical", "high", "medium", "low", "info"]

_AGENT_ICONS = {
    "security": "🔒",
    "quality": "⚙️",
    "testing": "🧪",
    "documentation": "📝",
    "ticket_compliance": "🎫",
}

_SEVERITY_ICONS = {
    "critical": "🔴",
    "high": "🟠",
    "medium": "🟡",
    "low": "🟢",
    "info": "⚪",
}

_AGENT_ORDER = ("security", "quality", "testing", "documentation", "ticket_compliance")


def _build_fence(text: str, language: str = "") -> tuple[str, str]:
    longest = max((len(run) for run in re.findall(r"`+", text)), default=0)
    fence = "`" * max(3, longest + 1)
    return f"{fence}{language}", fence


def _severity_badge(severity: str, count: int) -> str:
    icon = _SEVERITY_ICONS.get(severity, "⚪")
    return f"{icon}&nbsp;{count}&nbsp;{severity}"


def format_findings(findings: list[FindingSchema]) -> str:
    if not findings:
        return "✅ **Argus Review complete** — no issues found across all agents."

    by_agent: dict[str, dict[str, list[FindingSchema]]] = {}
    for f in findings:
        by_agent.setdefault(f.agent, {}).setdefault(f.severity, []).append(f)

    ordered = [k for k in _AGENT_ORDER if k in by_agent]
    ordered += [k for k in by_agent if k not in _AGENT_ORDER]

    header_cols = ["| Agent |"] + [f" {_SEVERITY_ICONS[s]} {s.capitalize()} |" for s in _SEVERITY_ORDER]
    sep_cols = ["|---|"] + [":---:|" for _ in _SEVERITY_ORDER]
    table_rows = []
    for agent_key in ordered:
        icon = _AGENT_ICONS.get(agent_key, "🤖")
        label = _AGENT_LABELS.get(agent_key, agent_key.title())
        row = f"| {icon} **{label}** |"
        for sev in _SEVERITY_ORDER:
            count = len(by_agent[agent_key].get(sev, []))
            row += f" {'**' + str(count) + '**' if count else '—'} |"
        table_rows.append(row)

    auto_fixes = sum(1 for f in findings if f.fix and f.fix.diff)
    total = len(findings)

    lines = [
        "## 🛡 Argus Code Review",
        "",
        "".join(header_cols),
        "".join(sep_cols),
        "\n".join(table_rows),
        "",
        f"> **{total} findings** · 🔧 **{auto_fixes} auto-fixes** available — accept them in the **Files changed** tab",
        "",
        "---",
        "",
    ]

    for agent_key in ordered:
        icon = _AGENT_ICONS.get(agent_key, "🤖")
        label = _AGENT_LABELS.get(agent_key, agent_key.title())
        agent_findings = by_agent[agent_key]
        agent_total = sum(len(v) for v in agent_findings.values())

        badges = " &nbsp; ".join(_severity_badge(s, len(agent_findings[s])) for s in _SEVERITY_ORDER if agent_findings.get(s))
        summary_line = f"{icon} **{label}** &nbsp;—&nbsp; {agent_total} findings &nbsp; {badges}"

        lines.append("<details>")
        lines.append(f"<summary>{summary_line}</summary>")
        lines.append("")

        for severity in _SEVERITY_ORDER:
            bucket = agent_findings.get(severity, [])
            if not bucket:
                continue
            sev_icon = _SEVERITY_ICONS.get(severity, "⚪")
            lines.append(f"#### {sev_icon} {severity.upper()}")
            lines.append("")
            for finding in bucket:
                lines.append(f"**{finding.title}**")
                lines.append(f"`{finding.file}:{finding.line_start}`")
                lines.append("")
                lines.append(finding.description)
                lines.append("")
                if finding.suggestion:
                    lines.append(f"> 💡 {finding.suggestion}")
                    lines.append("")
                if finding.fix and finding.fix.diff:
                    lines.append("<details>")
                    lines.append(f"<summary>🔧 Suggested fix — <i>{finding.fix.description}</i></summary>")
                    lines.append("")
                    open_fence, close_fence = _build_fence(finding.fix.diff, "diff")
                    lines.append(open_fence)
                    lines.append(finding.fix.diff)
                    lines.append(close_fence)
                    lines.append("")
                    lines.append("</details>")
                    lines.append("")
                lines.append("---")
                lines.append("")

        lines.append("</details>")
        lines.append("")

    return "\n".join(lines)
