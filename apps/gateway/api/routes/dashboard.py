from __future__ import annotations

from collections.abc import Sequence

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import HTMLResponse
from shared.config import get_settings
from shared.dashboard_token import verify
from shared.db import session_context
from shared.models import Finding as FindingModel
from shared.models import Repo, Review
from sqlalchemy import select

router = APIRouter()

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

# ── CSS (plain string — no f-string escaping needed) ────────────────────────
_CSS = """
:root[data-theme="dark"] {
  --bg: #0d1117;
  --surface: #161b22;
  --surface2: #21262d;
  --surface3: #30363d;
  --border: #30363d;
  --text: #e6edf3;
  --text-muted: #8b949e;
  --text-subtle: #6e7681;
  --accent: #58a6ff;
  --accent-bg: rgba(88,166,255,.12);
  --shadow: 0 1px 4px rgba(0,0,0,.5);
  --sev-critical:#f85149; --sev-critical-bg:rgba(248,81,73,.15);
  --sev-high:#fb8500;     --sev-high-bg:rgba(251,133,0,.15);
  --sev-medium:#e3b341;   --sev-medium-bg:rgba(227,179,65,.15);
  --sev-low:#3fb950;      --sev-low-bg:rgba(63,185,80,.15);
  --sev-info:#8b949e;     --sev-info-bg:rgba(139,148,158,.12);
  --sug-bg:rgba(88,166,255,.08);
  --sug-border:rgba(88,166,255,.3);
  --sug-header:rgba(88,166,255,.18);
}
:root[data-theme="light"] {
  --bg: #f6f8fa;
  --surface: #ffffff;
  --surface2: #f6f8fa;
  --surface3: #eaecef;
  --border: #d0d7de;
  --text: #1f2328;
  --text-muted: #656d76;
  --text-subtle: #909dab;
  --accent: #0969da;
  --accent-bg: rgba(9,105,218,.08);
  --shadow: 0 1px 3px rgba(0,0,0,.1);
  --sev-critical:#cf222e; --sev-critical-bg:#fff5f5;
  --sev-high:#bc4c00;     --sev-high-bg:#fff8f0;
  --sev-medium:#9a6700;   --sev-medium-bg:#fffbe6;
  --sev-low:#1a7f37;      --sev-low-bg:#f0fff4;
  --sev-info:#57606a;     --sev-info-bg:#f6f8fa;
  --sug-bg:#ddf4ff;
  --sug-border:#54aeff;
  --sug-header:#cae8ff;
}

*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
body{
  font-family:-apple-system,BlinkMacSystemFont,'Segoe UI','Noto Sans',sans-serif;
  background:var(--bg);color:var(--text);font-size:14px;line-height:1.5;
  transition:background .2s,color .2s;
}

/* ── HEADER ── */
header{
  background:var(--surface);border-bottom:1px solid var(--border);
  padding:14px 24px;display:flex;align-items:center;
  justify-content:space-between;gap:12px;
  position:sticky;top:0;z-index:100;box-shadow:var(--shadow);
}
.h-left{display:flex;align-items:center;gap:12px}
.h-logo{font-size:1.7rem;line-height:1}
.h-title h1{font-size:1rem;font-weight:700}
.h-meta{font-size:.78rem;color:var(--text-muted);margin-top:2px}
.h-right{display:flex;align-items:center;gap:10px;flex-shrink:0}
.status-pill{
  padding:5px 14px;border-radius:99px;font-size:.75rem;
  font-weight:700;color:#fff;white-space:nowrap;
}
.status-bad{background:#cf222e}
.status-ok{background:#1a7f37}
.theme-btn{
  background:var(--surface2);border:1px solid var(--border);
  border-radius:8px;padding:6px 11px;cursor:pointer;
  font-size:.95rem;color:var(--text);transition:border-color .15s;
}
.theme-btn:hover{border-color:var(--accent)}

/* ── LAYOUT ── */
.container{max-width:1080px;margin:0 auto;padding:24px 16px}

/* ── STATS STRIP ── */
.stats-strip{display:flex;gap:10px;margin-bottom:20px;flex-wrap:wrap}
.stat{
  background:var(--surface);border:1px solid var(--border);
  border-radius:10px;padding:14px 18px;display:flex;
  flex-direction:column;align-items:center;gap:3px;
  flex:1;min-width:76px;box-shadow:var(--shadow);
}
.stat-icon{font-size:1.05rem}
.stat-count{font-size:1.45rem;font-weight:800}
.stat-label{font-size:.67rem;color:var(--text-muted);text-transform:uppercase;letter-spacing:.06em}
.stat.sev-critical .stat-count{color:var(--sev-critical)}
.stat.sev-high     .stat-count{color:var(--sev-high)}
.stat.sev-medium   .stat-count{color:var(--sev-medium)}
.stat.sev-low      .stat-count{color:var(--sev-low)}
.stat.sev-info     .stat-count{color:var(--sev-info)}

/* ── SUMMARY CARD ── */
.summary-card{
  background:var(--surface);border:1px solid var(--border);
  border-radius:12px;padding:20px;margin-bottom:20px;box-shadow:var(--shadow);
}
.card-heading{
  font-size:.75rem;font-weight:700;color:var(--text-muted);
  text-transform:uppercase;letter-spacing:.08em;margin-bottom:14px;
}
table{width:100%;border-collapse:collapse;font-size:.875rem}
th{
  text-align:left;padding:8px 12px;color:var(--text-muted);
  font-weight:500;border-bottom:1px solid var(--border);font-size:.78rem;
}
td{padding:10px 12px;border-bottom:1px solid var(--border)}
tr:last-child td{border-bottom:none}
.agent-cell{font-weight:500}
.cnt{
  display:inline-block;border-radius:99px;
  padding:2px 8px;font-size:.72rem;font-weight:700;
}
.cnt-critical{background:var(--sev-critical-bg);color:var(--sev-critical)}
.cnt-high    {background:var(--sev-high-bg);    color:var(--sev-high)}
.cnt-medium  {background:var(--sev-medium-bg);  color:var(--sev-medium)}
.cnt-low     {background:var(--sev-low-bg);     color:var(--sev-low)}
.cnt-info    {background:var(--sev-info-bg);    color:var(--sev-info)}
.cnt-zero    {color:var(--text-subtle)}

/* ── FILTER BAR ── */
.filter-bar{
  display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin-bottom:16px;
}
.filter-label{font-size:.78rem;color:var(--text-muted);font-weight:600;margin-right:2px}
.filter-chip{
  background:var(--surface);border:1.5px solid var(--border);
  border-radius:99px;padding:5px 14px;font-size:.78rem;font-weight:500;
  color:var(--text-muted);cursor:pointer;transition:all .15s;
  display:inline-flex;align-items:center;gap:5px;
}
.filter-chip:hover{border-color:var(--accent);color:var(--accent)}
.filter-chip.active{background:var(--accent);border-color:var(--accent);color:#fff}
.fc-n{
  background:var(--surface3);color:var(--text-subtle);
  border-radius:99px;padding:0 6px;font-size:.68rem;
}
.filter-chip.active .fc-n{background:rgba(255,255,255,.25);color:#fff}

/* ── TABS ── */
.tabs{
  display:flex;gap:2px;margin-bottom:16px;
  background:var(--surface2);border-radius:10px;
  padding:4px;border:1px solid var(--border);flex-wrap:wrap;
}
.tab{
  background:transparent;border:none;border-radius:7px;
  padding:8px 16px;font-size:.875rem;font-weight:500;
  color:var(--text-muted);cursor:pointer;transition:all .15s;
  display:inline-flex;align-items:center;gap:6px;
}
.tab:hover{color:var(--text);background:var(--surface3)}
.tab.active{background:var(--surface);color:var(--text);box-shadow:var(--shadow)}
.badge{
  background:var(--surface3);color:var(--text-muted);
  border-radius:99px;padding:1px 7px;font-size:.7rem;font-weight:600;
}
.tab.active .badge{background:var(--accent-bg);color:var(--accent)}

/* ── PANELS ── */
.panel{display:none}
.panel.active{display:block}

/* ── SEV GROUP ── */
.sev-group{margin-bottom:6px}
.sev-group-header{
  font-size:.7rem;font-weight:700;text-transform:uppercase;
  letter-spacing:.08em;padding:12px 4px 8px;
  display:flex;align-items:center;gap:8px;
}
.sev-group-header .gc{
  background:var(--surface3);border-radius:99px;
  padding:1px 8px;font-size:.68rem;color:var(--text-muted);font-weight:600;
}
.sev-group-header.sev-critical{color:var(--sev-critical)}
.sev-group-header.sev-high    {color:var(--sev-high)}
.sev-group-header.sev-medium  {color:var(--sev-medium)}
.sev-group-header.sev-low     {color:var(--sev-low)}
.sev-group-header.sev-info    {color:var(--sev-info)}

/* ── FINDING CARD ── */
.finding-card{
  background:var(--surface);border:1px solid var(--border);
  border-left:4px solid transparent;border-radius:10px;
  padding:16px 18px;margin-bottom:10px;
  box-shadow:var(--shadow);transition:box-shadow .15s,transform .1s;
}
.finding-card:hover{box-shadow:0 4px 16px rgba(0,0,0,.2);transform:translateY(-1px)}
.finding-card[data-severity="critical"]{border-left-color:var(--sev-critical)}
.finding-card[data-severity="high"]    {border-left-color:var(--sev-high)}
.finding-card[data-severity="medium"]  {border-left-color:var(--sev-medium)}
.finding-card[data-severity="low"]     {border-left-color:var(--sev-low)}
.finding-card[data-severity="info"]    {border-left-color:var(--sev-info)}
.card-meta{
  display:flex;align-items:center;gap:8px;flex-wrap:wrap;margin-bottom:10px;
}
.sev-badge{
  border-radius:4px;padding:3px 8px;font-size:.68rem;
  font-weight:800;text-transform:uppercase;letter-spacing:.06em;
}
.sev-badge.sev-critical{background:var(--sev-critical-bg);color:var(--sev-critical)}
.sev-badge.sev-high    {background:var(--sev-high-bg);    color:var(--sev-high)}
.sev-badge.sev-medium  {background:var(--sev-medium-bg);  color:var(--sev-medium)}
.sev-badge.sev-low     {background:var(--sev-low-bg);     color:var(--sev-low)}
.sev-badge.sev-info    {background:var(--sev-info-bg);    color:var(--sev-info)}
.agent-badge{
  background:var(--accent-bg);color:var(--accent);
  border-radius:4px;padding:3px 8px;font-size:.68rem;font-weight:600;
}
.file-chip{
  font-family:'SFMono-Regular',Consolas,'Liberation Mono',monospace;
  font-size:.72rem;background:var(--surface2);color:var(--text-muted);
  border:1px solid var(--border);border-radius:4px;padding:3px 8px;
  margin-left:auto;
}
.card-title{font-size:.95rem;font-weight:700;margin-bottom:6px}
.card-desc{font-size:.875rem;color:var(--text-muted);line-height:1.65}

/* ── SUGGESTION BLOCK ── */
.suggestion-block{
  margin-top:14px;border:1px solid var(--sug-border);
  border-radius:8px;overflow:hidden;
}
.suggestion-header{
  background:var(--sug-header);border-bottom:1px solid var(--sug-border);
  padding:7px 14px;font-size:.75rem;font-weight:700;
  color:var(--accent);display:flex;align-items:center;gap:6px;
}
.suggestion-body{
  padding:12px 14px;font-size:.875rem;color:var(--text);
  line-height:1.65;background:var(--sug-bg);
  white-space:pre-wrap;word-break:break-word;
}

/* ── EMPTY ── */
.empty-state{
  text-align:center;padding:48px 0;color:var(--text-muted);font-size:.9rem;
}

/* ── RESPONSIVE ── */
@media(max-width:640px){
  header{padding:12px 14px}
  .h-title h1{font-size:.9rem}
  .stats-strip{gap:6px}
  .stat{min-width:56px;padding:10px 8px}
  .stat-count{font-size:1.1rem}
  .container{padding:16px 10px}
  .file-chip{margin-left:0;margin-top:4px}
}
"""

# ── JS (plain string — no f-string escaping needed) ─────────────────────────
_JS = """
// Theme
function toggleTheme() {
  const html = document.documentElement;
  const next = html.dataset.theme === 'dark' ? 'light' : 'dark';
  html.dataset.theme = next;
  document.getElementById('theme-btn').textContent = next === 'dark' ? '☀️' : '🌙';
  localStorage.setItem('argus-theme', next);
}
(function () {
  const saved = localStorage.getItem('argus-theme') || 'dark';
  document.documentElement.dataset.theme = saved;
  const btn = document.getElementById('theme-btn');
  if (btn) btn.textContent = saved === 'dark' ? '☀️' : '🌙';
})();

// Tabs
const tabs   = document.querySelectorAll('.tab');
const panels = document.querySelectorAll('.panel');
tabs.forEach(tab => {
  tab.addEventListener('click', () => {
    tabs.forEach(t => t.classList.remove('active'));
    panels.forEach(p => p.classList.remove('active'));
    tab.classList.add('active');
    const panel = document.getElementById('panel-' + tab.dataset.tab);
    if (panel) panel.classList.add('active');
    applyFilter(document.querySelector('.filter-chip.active')?.dataset.filter || 'all');
  });
});
if (panels[0]) panels[0].classList.add('active');

// Filtering
function applyFilter(filter) {
  const active = document.querySelector('.panel.active');
  if (!active) return;
  active.querySelectorAll('.finding-card').forEach(card => {
    const show = filter === 'all'
      || (filter === 'has-suggestion' && card.dataset.hasSuggestion === 'true')
      || card.dataset.severity === filter;
    card.style.display = show ? '' : 'none';
  });
  active.querySelectorAll('.sev-group').forEach(grp => {
    const visible = [...grp.querySelectorAll('.finding-card')]
      .some(c => c.style.display !== 'none');
    grp.style.display = visible ? '' : 'none';
  });
}
document.querySelectorAll('.filter-chip').forEach(chip => {
  chip.addEventListener('click', () => {
    document.querySelectorAll('.filter-chip').forEach(c => c.classList.remove('active'));
    chip.classList.add('active');
    applyFilter(chip.dataset.filter);
  });
});
"""


@router.get("/{owner}/{repo}/{pr_number}", response_class=HTMLResponse)
async def review_dashboard(
    owner: str,
    repo: str,
    pr_number: int,
    token: str = Query(...),
):
    settings = get_settings()
    repo_full_name = f"{owner}/{repo}"

    signing_secret = settings.dashboard_token_secret or settings.jwt_secret_key
    if not verify(signing_secret, token, repo_full_name, pr_number):
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
    findings: Sequence[FindingModel],
) -> str:
    by_agent: dict[str, list[FindingModel]] = {}
    for f in findings:
        by_agent.setdefault(f.agent, []).append(f)

    agents = [a for a in _AGENT_ORDER if a in by_agent]
    agents += [a for a in by_agent if a not in _AGENT_ORDER]

    total = len(findings)
    counts = {s: sum(1 for f in findings if f.severity == s) for s in _SEVERITY_ORDER}
    has_critical_or_high = counts["critical"] > 0 or counts["high"] > 0
    completed = review.completed_at.strftime("%Y-%m-%d %H:%M UTC") if review.completed_at else "—"

    # ── Stats strip ─────────────────────────────────────────────────────────
    stats_html = "".join(f'<div class="stat sev-{s}"><span class="stat-icon">{_SEVERITY_ICONS.get(s, "⚪")}</span><span class="stat-count">{counts[s]}</span><span class="stat-label">{s.capitalize()}</span></div>' for s in _SEVERITY_ORDER)

    # ── Summary table ────────────────────────────────────────────────────────
    th_cells = "".join(f"<th>{_SEVERITY_ICONS.get(s, '⚪')} {s.capitalize()}</th>" for s in _SEVERITY_ORDER)
    table_rows = ""
    for agent in agents:
        icon = _AGENT_ICONS.get(agent, "🤖")
        label = agent.replace("_", " ").title()
        row = f'<tr><td class="agent-cell">{icon} {label}</td>'
        for sev in _SEVERITY_ORDER:
            c = sum(1 for f in by_agent.get(agent, []) if f.severity == sev)
            row += f'<td><span class="cnt cnt-{sev}">{c}</span></td>' if c else '<td><span class="cnt-zero">—</span></td>'
        row += "</tr>"
        table_rows += row

    # ── Filter chips ─────────────────────────────────────────────────────────
    filter_chips = '<button class="filter-chip active" data-filter="all">All</button>\n'
    for sev in _SEVERITY_ORDER:
        if counts[sev]:
            filter_chips += f'<button class="filter-chip" data-filter="{sev}">{_SEVERITY_ICONS.get(sev, "⚪")} {sev.capitalize()} <span class="fc-n">{counts[sev]}</span></button>\n'
    suggestions_count = sum(1 for f in findings if f.suggestion)
    if suggestions_count:
        filter_chips += f'<button class="filter-chip" data-filter="has-suggestion">💡 Has Suggestion <span class="fc-n">{suggestions_count}</span></button>\n'

    # ── Tab buttons ──────────────────────────────────────────────────────────
    tab_buttons = f'<button class="tab active" data-tab="all">All <span class="badge">{total}</span></button>\n'
    for agent in agents:
        n = len(by_agent[agent])
        icon = _AGENT_ICONS.get(agent, "🤖")
        label = agent.replace("_", " ").title()
        tab_buttons += f'<button class="tab" data-tab="{agent}">{icon} {label} <span class="badge">{n}</span></button>\n'

    # ── Panels ───────────────────────────────────────────────────────────────
    def render_card(f: FindingModel) -> str:
        sev = f.severity
        agent_label = f.agent.replace("_", " ").title()
        file_loc = f"{_esc(f.file)}:{f.line_start}"
        if f.line_end and f.line_end != f.line_start:
            file_loc += f"–{f.line_end}"
        suggestion_html = ""
        if f.suggestion:
            suggestion_html = f'<div class="suggestion-block"><div class="suggestion-header">💡 Suggested change</div><div class="suggestion-body">{_esc(f.suggestion)}</div></div>'
        sev_esc = _esc(sev)
        agent_esc = _esc(f.agent)
        return (
            f'<div class="finding-card" data-severity="{sev_esc}" data-agent="{agent_esc}"'
            f' data-has-suggestion="{"true" if f.suggestion else "false"}">'
            f'<div class="card-meta">'
            f'<span class="sev-badge sev-{sev_esc}">{_SEVERITY_ICONS.get(sev, "⚪")} {sev_esc.upper()}</span>'
            f'<span class="agent-badge">{_AGENT_ICONS.get(f.agent, "🤖")} {_esc(agent_label)}</span>'
            f'<span class="file-chip">{file_loc}</span>'
            f"</div>"
            f'<div class="card-title">{_esc(f.title)}</div>'
            f'<div class="card-desc">{_esc(f.description)}</div>'
            f"{suggestion_html}"
            f"</div>"
        )

    def render_panel(panel_id: str, panel_findings: list[FindingModel]) -> str:
        if not panel_findings:
            return f'<div class="panel" id="panel-{panel_id}"><div class="empty-state">✅ No findings here.</div></div>'
        body = ""
        for sev in _SEVERITY_ORDER:
            bucket = [f for f in panel_findings if f.severity == sev]
            if not bucket:
                continue
            icon = _SEVERITY_ICONS.get(sev, "⚪")
            body += f'<div class="sev-group" data-sev="{sev}"><div class="sev-group-header sev-{sev}">{icon} {sev.upper()} <span class="gc">{len(bucket)}</span></div>'
            for f in bucket:
                body += render_card(f)
            body += "</div>"
        return f'<div class="panel" id="panel-{panel_id}">{body}</div>'

    panels_html = render_panel("all", list(findings))
    for agent in agents:
        panels_html += render_panel(agent, by_agent[agent])

    status_label = f"{'❌' if has_critical_or_high else '✅'} {total} findings"
    status_cls = "status-bad" if has_critical_or_high else "status-ok"

    return f"""<!DOCTYPE html>
<html data-theme="dark" lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Argus · {_esc(repo_full_name)} · PR #{pr_number}</title>
<style>{_CSS}</style>
</head>
<body>
<header>
  <div class="h-left">
    <span class="h-logo">🛡</span>
    <div class="h-title">
      <h1>Argus Code Review</h1>
      <div class="h-meta">{_esc(repo_full_name)} &nbsp;·&nbsp; PR #{pr_number} &nbsp;·&nbsp; {completed}</div>
    </div>
  </div>
  <div class="h-right">
    <span class="status-pill {status_cls}">{status_label}</span>
    <button class="theme-btn" id="theme-btn" onclick="toggleTheme()" title="Toggle dark / light mode">☀️</button>
  </div>
</header>

<div class="container">

  <div class="stats-strip">
    {stats_html}
  </div>

  <div class="summary-card">
    <div class="card-heading">Summary by Agent</div>
    <table>
      <tr><th>Agent</th>{th_cells}</tr>
      {table_rows}
    </table>
  </div>

  <div class="filter-bar">
    <span class="filter-label">Filter:</span>
    {filter_chips}
  </div>

  <div class="tabs">{tab_buttons}</div>

  <div id="panels">{panels_html}</div>

</div>
<script>{_JS}</script>
</body>
</html>"""


def _esc(text: str) -> str:
    return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")
