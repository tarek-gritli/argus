# Documentation Agent

Analyzes pull request diffs for documentation quality issues and auto-generates missing docs using Gemini 2.0 Flash.

---

## Architecture

```text
PR Diff
  │
  ├─► Static Checks (no LLM, instant)
  │     ├─ missing_docstrings.py   — public def/class without docstring
  │     ├─ param_coverage.py       — undocumented Args / Returns
  │     ├─ stale_comments.py       — TODO/FIXME without ticket, commented-out code
  │     └─ readme_gaps.py          — new modules or env vars without README update
  │
  ├─► Gemini: Docstring Generation
  │     └─ Batch-generates Google-style docstrings for all missing-docstring findings
  │        Attaches them as fix.diff → one-click suggestion on GitHub
  │
  ├─► Gemini: Qualitative Review
  │     └─ Reviews the diff for issues static checks can't catch:
  │        misleading descriptions, wrong terminology, outdated explanations
  │
  ├─► Merge + Dedup
  │     └─ Combines static + LLM findings, drops duplicates by (file, line, title)
  │
  └─► Validate → list[FindingSchema]
        └─ Min confidence 0.55 · Max 15 findings · Sorted by severity
```

---

## What It Does

| Capability | How |
|---|---|
| Detects missing docstrings | Regex on added `def`/`class` lines in diff |
| Detects undocumented params | AST-parses added `def` signatures; checks `Args:`/`Returns:` coverage in docstrings |
| Flags stale comments | Finds TODO/FIXME/HACK without a ticket reference |
| Spots commented-out code | Detects `# <code>` blocks in added lines |
| Catches README gaps | New `os.environ.get(...)` or new modules without README mention |
| Generates docstrings | Single Gemini call → Google-style docstring as a GitHub suggestion |
| Qualitative review | Gemini reads full diff for semantic doc issues |
| Auto PR description | Detects PR type (Feature/Bug Fix/Hotfix/Improvement/Refactor) and fills the matching template; skips if the existing body already contains substantial non-template content |

---

## Gemini Integration

- **Model:** `gemini-2.0-flash` (free tier, 1M token context)
- **Calls per PR:** up to 3 (docstring gen + qualitative review + PR description)
- **Fallback:** if Gemini is unavailable or rate-limited, static findings are still posted — the agent never blocks the pipeline
- **Rate limit handling:** auto-retry with the delay Gemini returns; daily quota exhaustion is detected immediately and skipped without retrying

---

## Output

Each finding is a `FindingSchema` with:
- `file`, `line_start`, `line_end`, `severity`, `title`, `description`
- `fix.diff` — ready-to-apply docstring patch (when Gemini is available)

Findings are posted as inline GitHub review comments. Those with a `fix.diff` appear as one-click **suggestion** blocks the author can accept directly on GitHub.

---

## Files

```text
specialized/documentation/
├── agent.py            — main pipeline entry point
├── gemini_client.py    — shared Gemini call with retry logic
├── pr_description.py   — PR description auto-generation
├── validator.py        — confidence filter + cap
├── schemas.py          — AgentInput dataclass
└── checks/
    ├── missing_docstrings.py
    ├── param_coverage.py
    ├── stale_comments.py
    └── readme_gaps.py
```
