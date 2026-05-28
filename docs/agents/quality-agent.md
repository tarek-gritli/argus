# Quality Agent

Analyzes pull request diffs for code-quality issues and uses Claude to turn deterministic evidence into actionable review findings.

---

## Architecture

```text
PR Diff
  │
  ├─► Static Analysis (no LLM, instant)
  │     ├─ ast_analyzer.py      — cyclomatic complexity, nesting, magic numbers, duplicates
  │     └─ grep_patterns.py     — debug prints, TODOs, commented-out code, mutable defaults
  │
  ├─► Deterministic Checks
  │     ├─ complexity.py        — deep control flow and branch-heavy functions
  │     ├─ duplication.py       — repeated logic / repeated blocks
  │     ├─ dead_code.py         — unused imports, dead paths, stale code smells
  │     └─ structure.py         — long functions, magic numbers, readability issues
  │
  ├─► Claude: Quality Review
  │     └─ Reviews the diff plus static evidence for real maintainability issues
  │
  ├─► Validate + Dedup
  │     └─ Drops shallow metric echoes, enforces confidence floor, caps findings
  │
  └─► Output → list[FindingSchema]
        └─ Confidence policy is shared with the other specialized agents
```

---

## What It Does

| Capability | How |
|---|---|
| Detects deep complexity | AST walks functions and scores cyclomatic complexity / nesting |
| Spots duplicated logic | Hashes normalized code blocks and looks for repeated segments |
| Flags dead code signals | Finds unused imports, commented-out code, and stale branches |
| Catches structure problems | Reports long functions, magic numbers, and noisy readability issues |
| Uses shared confidence policy | Validator drops low-confidence or metric-echo findings and sorts the rest |
| Produces review findings | Returns `FindingSchema` objects for inline code review |

---

## Claude Integration

- **Model:** `claude-haiku-4-5`
- **Calls per PR:** 1
- **Fallback:** deterministic findings still run; the validator filters and returns only what clears the policy
- **Confidence handling:** deterministic checks score evidence, then `validator.py` filters low-confidence and shallow findings using the shared confidence helpers

---

## Output

Each finding is a `FindingSchema` with:
- `file`, `line_start`, `line_end`, `severity`, `title`, `description`
- `suggestion` with a concrete cleanup or refactor
- `confidence` normalized by the shared specialized confidence policy

Findings are sorted by severity and confidence before being returned to the orchestrator.

---

## Files

```text
specialized/quality/
├── agent.py            — main pipeline entry point
├── validator.py        — shared confidence policy + cleanup
├── schemas.py          — AgentInput dataclass
├── prompts/system.py   — Claude system prompt
├── confidence.py       — shared confidence helpers
├── tools/
│   ├── ast_analyzer.py — AST metrics and static summaries
│   └── grep_patterns.py — diff pattern scanner
└── checks/
    ├── complexity.py
    ├── duplication.py
    ├── dead_code.py
    └── structure.py
```