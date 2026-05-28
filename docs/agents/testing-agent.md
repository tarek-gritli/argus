# Testing Agent

Analyzes pull request diffs for missing or weak tests and uses Claude to turn coverage signals into actionable test-review findings.

---

## Architecture

```text
PR Diff
  │
  ├─► Static Analysis (no LLM, instant)
  │     ├─ coverage_analyzer.py — public symbols, test functions, assertion density
  │     └─ test_patterns.py     — weak assertions, sleep calls, bare excepts, assertionless tests
  │
  ├─► Claude: Test Review
  │     └─ Reviews the diff plus coverage signals for test gaps and test anti-patterns
  │
  ├─► Validate + Dedup
  │     └─ Penalizes speculative "no tests" claims, enforces confidence floor, caps findings
  │
  └─► Output → list[FindingSchema]
        └─ Confidence policy is shared with the other specialized agents
```

---

## What It Does

| Capability | How |
|---|---|
| Detects missing tests | Finds added public code with no matching test-name references in the diff |
| Measures test quality | Counts assertions, fixtures, and parametrization in changed test files |
| Flags weak assertions | Detects trivially true assertions and broad checks in new tests |
| Spots flaky patterns | Reports sleep calls, bare excepts, and assertionless test bodies |
| Penalizes speculation | Reduces confidence when the diff touches test files and the agent is guessing about coverage |
| Produces review findings | Returns `FindingSchema` objects for inline code review |

---

## Claude Integration

- **Model:** `claude-haiku-4-5`
- **Calls per PR:** 1
- **Fallback:** deterministic findings still run; the validator filters and returns only what clears the policy
- **Confidence handling:** coverage and pattern signals are surfaced to Claude, then `validator.py` lowers confidence for speculative claims and drops weak findings

---

## Output

Each finding is a `FindingSchema` with:
- `file`, `line_start`, `line_end`, `severity`, `title`, `description`
- `suggestion` describing the test to add or the assertion to tighten
- `confidence` normalized by the shared specialized confidence policy

Findings are sorted by severity and confidence before being returned to the orchestrator.

---

## Files

```text
specialized/testing/
├── agent.py            — main pipeline entry point
├── validator.py        — shared confidence policy + speculative-claim penalties
├── schemas.py          — AgentInput dataclass
├── prompts/system.py   — Claude system prompt
└── tools/
    ├── coverage_analyzer.py — coverage heuristics and assertion metrics
    └── test_patterns.py     — diff pattern scanner for test smells
```