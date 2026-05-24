# Argus Agents

LangGraph-based agent orchestration for parallel code review.

## Agents

**Active on all plans:**
1. **Security** — OWASP vulnerability detection, secrets exposure, OSV CVE scanning
2. **Quality** — complexity, duplication, dead code, naming
3. **Testing** — coverage gaps, weak assertions, test anti-patterns

**Team/Enterprise only (stubs on free/pro):**
4. **Documentation** — PR description auto-generation, docstring completeness
5. **Ticket Compliance** — links PR changes to issue tracker requirements, flags scope drift ✅

## Architecture

```
Celery Task (review_pr)
         │
         ▼
┌─────────────────┐
│  Coordinator    │  fetches diff + context, checks quota, persists results
└────────┬────────┘
         │ LangGraph fan-out
    ┌────┴─────┬──────────┐
    ▼          ▼          ▼
Security    Quality    Testing
 Agent       Agent      Agent
    └────┬─────┴──────────┘
         │ merged findings
         ▼
  ┌─────────────┐
  │ Fix Engine  │  generator → validator → scorer
  └──────┬──────┘
         │
  GitHub PR Review (inline suggestions + summary comment)
```

## Fix Engine

Runs after agents complete. For each qualifying finding (severity ≥ medium, confidence ≥ 0.7):
1. **Generator** — Claude produces a unified diff patch
2. **Validator** — multi-language syntax check (Python AST, JSON, Go/Rust/JS/TS)
3. **Scorer** — weights by severity and patch churn; discards low-confidence patches
4. Attached as `FixSchema` on the finding, posted as native GitHub `suggestion` block