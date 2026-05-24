from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import HTMLResponse
from shared.config import get_settings
from shared.dashboard_token import verify
from shared.db import session_context
from shared.models import Finding as FindingModel
from shared.models import Repo, Review
from sqlalchemy import select

router = APIRouter()

_SEVERITY_COLOR = {
    "critical": "#dc2626",
    "high": "#ea580c",
    "medium": "#d97706",
    "low": "#16a34a",
    "info": "#6b7280",
}

_SEVERITY_BG = {
    "critical": "#fef2f2",
    "high": "#fff7ed",
    "medium": "#fffbeb",
    "low": "#f0fdf4",
    "info": "#f9fafb",
}

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
_SEVERITY_ORDER = ("critical", "high", "medium", "low", "info")


@router.get("/{owner}/{repo}/{pr_number}", response_class=HTMLResponse)
async def review_dashboard(
    owner: str,
    repo: str,
    pr_number: int,
    token: str = Query(...),
):
    settings = get_settings()
    repo_full_name = f"{owner}/{repo}"

    if not verify(settings.jwt_secret_key, token, repo_full_name, pr_number):
        raise HTTPException(status_code=403, detail="Invalid or expired dashboard token")

    async with session_context() as session:
        repo_result = await session.execute(select(Repo).where(Repo.full_name == repo_full_name))
        repo_obj = repo_result.scalar_one_or_none()

        if not repo_obj:
            raise HTTPException(status_code=404, detail="Repository not found")

        review_result = await session.execute(select(Review).where(Review.repo_id == repo_obj.id, Review.pr_number == pr_number).order_by(Review.created_at.desc()).limit(1))
        review = review_result.scalar_one_or_none()

        if not review:
            raise HTTPException(status_code=404, detail="No review found for this PR")

        findings_result = await session.execute(select(FindingModel).where(FindingModel.review_id == review.id).order_by(FindingModel.severity, FindingModel.file))
        findings = findings_result.scalars().all()

    return HTMLResponse(_render_dashboard(repo_full_name, pr_number, review, findings))


def _render_dashboard(
    repo_full_name: str,
    pr_number: int,
    review: Review,
    findings: list[FindingModel],
) -> str:
    by_agent: dict[str, list[FindingModel]] = {}
    for f in findings:
        by_agent.setdefault(f.agent, []).append(f)

    agents = [a for a in _AGENT_ORDER if a in by_agent]
    agents += [a for a in by_agent if a not in _AGENT_ORDER]

    # Summary counts per agent per severity
    def count(agent: str, sev: str) -> int:
        return sum(1 for f in by_agent.get(agent, []) if f.severity == sev)

    total = len(findings)
    critical_count = sum(1 for f in findings if f.severity == "critical")
    high_count = sum(1 for f in findings if f.severity == "high")

    # Tab radio inputs
    tab_inputs = '<input type="radio" name="tab" id="tab-all" checked>\n'
    for agent in agents:
        tab_inputs += f'<input type="radio" name="tab" id="tab-{agent}">\n'

    # Tab labels
    tab_labels = '<label for="tab-all">All <span class="badge">{}</span></label>\n'.format(total)
    for agent in agents:
        n = len(by_agent[agent])
        icon = _AGENT_ICONS.get(agent, "🤖")
        label = agent.replace("_", " ").title()
        tab_labels += f'<label for="tab-{agent}">{icon} {label} <span class="badge">{n}</span></label>\n'

    # CSS tab selectors
    css_selectors = "#tab-all:checked ~ .panels #panel-all { display: block; }\n"
    for agent in agents:
        css_selectors += f"#tab-{agent}:checked ~ .panels #panel-{agent} {{ display: block; }}\n"
    # Active tab label highlighting
    css_active = "#tab-all:checked ~ .tabs label[for='tab-all'],\n"
    css_active += ",\n".join(f"#tab-{a}:checked ~ .tabs label[for='tab-{a}']" for a in agents)
    css_active += " { background:#2563eb; color:#fff; border-color:#2563eb; }\n"

    # Finding cards
    def render_finding(f: FindingModel) -> str:
        color = _SEVERITY_COLOR.get(f.severity, "#6b7280")
        bg = _SEVERITY_BG.get(f.severity, "#f9fafb")
        icon = _SEVERITY_ICONS.get(f.severity, "⚪")
        suggestion_html = ""
        if f.suggestion:
            suggestion_html = f'<div class="suggestion">💡 {_esc(f.suggestion)}</div>'
        return f"""
<div class="card" style="border-left:4px solid {color}; background:{bg}">
  <div class="card-header">
    <span class="sev-badge" style="background:{color}">{icon} {f.severity.upper()}</span>
    <span class="file-loc">{_esc(f.file)}:{f.line_start}</span>
  </div>
  <div class="card-title">{_esc(f.title)}</div>
  <div class="card-desc">{_esc(f.description)}</div>
  {suggestion_html}
</div>"""

    def render_panel(panel_id: str, panel_findings: list[FindingModel]) -> str:
        if not panel_findings:
            return f'<div class="panel" id="{panel_id}"><p class="empty">No findings.</p></div>'
        cards = ""
        for sev in _SEVERITY_ORDER:
            bucket = [f for f in panel_findings if f.severity == sev]
            if not bucket:
                continue
            icon = _SEVERITY_ICONS.get(sev, "⚪")
            cards += f'<h3 class="sev-header">{icon} {sev.upper()}</h3>\n'
            for f in bucket:
                cards += render_finding(f)
        return f'<div class="panel" id="{panel_id}">{cards}</div>'

    # All panel
    panels = render_panel("panel-all", list(findings))
    for agent in agents:
        panels += render_panel(f"panel-{agent}", by_agent[agent])

    # Summary table rows
    table_rows = ""
    for agent in agents:
        icon = _AGENT_ICONS.get(agent, "🤖")
        label = agent.replace("_", " ").title()
        row = f"<tr><td>{icon} {label}</td>"
        for sev in _SEVERITY_ORDER:
            c = count(agent, sev)
            color = _SEVERITY_COLOR.get(sev, "#6b7280")
            cell = f'<strong style="color:{color}">{c}</strong>' if c else '<span style="color:#d1d5db">—</span>'
            row += f"<td>{cell}</td>"
        row += "</tr>"
        table_rows += row

    status_color = "#dc2626" if critical_count or high_count else "#16a34a"
    status_label = f"{'❌' if critical_count or high_count else '✅'} {total} findings"

    completed = review.completed_at.strftime("%Y-%m-%d %H:%M UTC") if review.completed_at else "—"

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Argus Review · {_esc(repo_full_name)} · PR #{pr_number}</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #f1f5f9; color: #1e293b; }}
  header {{ background: #0f172a; color: #f8fafc; padding: 20px 32px; display: flex; align-items: center; gap: 16px; }}
  header h1 {{ font-size: 1.25rem; font-weight: 600; }}
  header .meta {{ font-size: 0.85rem; color: #94a3b8; }}
  .status-pill {{ padding: 4px 12px; border-radius: 99px; font-size: 0.8rem; font-weight: 600; background: {status_color}; color: #fff; }}
  .container {{ max-width: 1000px; margin: 0 auto; padding: 24px 16px; }}
  .summary-card {{ background: #fff; border-radius: 12px; padding: 20px; margin-bottom: 24px; box-shadow: 0 1px 3px rgba(0,0,0,.08); }}
  .summary-card h2 {{ font-size: 1rem; font-weight: 600; margin-bottom: 14px; color: #475569; }}
  table {{ width: 100%; border-collapse: collapse; font-size: 0.9rem; }}
  th {{ text-align: left; padding: 8px 12px; color: #64748b; font-weight: 500; border-bottom: 1px solid #e2e8f0; }}
  td {{ padding: 10px 12px; border-bottom: 1px solid #f1f5f9; }}
  tr:last-child td {{ border-bottom: none; }}
  /* CSS-only tabs */
  input[type=radio] {{ display: none; }}
  .tabs {{ display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 16px; }}
  .tabs label {{ padding: 8px 16px; border-radius: 8px; border: 1.5px solid #e2e8f0; cursor: pointer; font-size: 0.875rem; font-weight: 500; background: #fff; color: #475569; transition: all .15s; }}
  .tabs label:hover {{ border-color: #2563eb; color: #2563eb; }}
  {css_active}
  .badge {{ display: inline-block; background: #e2e8f0; color: #475569; border-radius: 99px; padding: 1px 7px; font-size: 0.75rem; margin-left: 4px; }}
  /* Panels */
  .panels .panel {{ display: none; }}
  {css_selectors}
  .card {{ border-radius: 10px; padding: 16px; margin-bottom: 12px; }}
  .card-header {{ display: flex; align-items: center; gap: 10px; margin-bottom: 8px; }}
  .sev-badge {{ color: #fff; border-radius: 4px; padding: 2px 8px; font-size: 0.75rem; font-weight: 700; }}
  .file-loc {{ font-family: monospace; font-size: 0.8rem; color: #64748b; background: rgba(0,0,0,.06); padding: 2px 6px; border-radius: 4px; }}
  .card-title {{ font-weight: 600; font-size: 0.95rem; margin-bottom: 6px; }}
  .card-desc {{ font-size: 0.875rem; color: #475569; line-height: 1.5; }}
  .suggestion {{ margin-top: 10px; padding: 10px 14px; background: rgba(37,99,235,.07); border-radius: 6px; font-size: 0.85rem; color: #1e40af; }}
  .sev-header {{ font-size: 0.85rem; font-weight: 700; color: #64748b; margin: 16px 0 8px; text-transform: uppercase; letter-spacing: .05em; }}
  .empty {{ color: #94a3b8; padding: 24px 0; text-align: center; }}
</style>
</head>
<body>
<header>
  <div>
    <h1>🛡 Argus Code Review</h1>
    <div class="meta">{_esc(repo_full_name)} · PR #{pr_number} · {completed}</div>
  </div>
  <span class="status-pill">{status_label}</span>
</header>

<div class="container">
  <div class="summary-card">
    <h2>Summary by agent</h2>
    <table>
      <tr>
        <th>Agent</th>
        {"".join(f"<th>{_SEVERITY_ICONS.get(s, '⚪')} {s.capitalize()}</th>" for s in _SEVERITY_ORDER)}
      </tr>
      {table_rows}
    </table>
  </div>

  {tab_inputs}
  <div class="tabs">
    {tab_labels}
  </div>
  <div class="panels">
    {panels}
  </div>
</div>
</body>
</html>"""


def _esc(text: str) -> str:
    return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")
