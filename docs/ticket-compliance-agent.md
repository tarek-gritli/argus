# Ticket Compliance Agent

Checks whether a PR's diff actually implements what a linked GitHub issue describes.

---

## Architecture

```text
PR Title + Body
  │
  ├─► Extract ticket refs (extractor.py)
  │     └─ Regex: #42, Closes #42, Fixes #42, Resolves #42
  │        Returns deduplicated list of (provider, issue_id) tuples
  │
  ├─► Resolve ticket (agent.py: _resolve_ticket)
  │     └─ Walks refs in order, tries each registered provider
  │        Returns first successfully fetched TicketData
  │        Provider failures are caught + logged; loop continues
  │
  ├─► Claude: Compliance Analysis
  │     └─ Compares issue description to PR diff
  │        Outputs JSON array of unimplemented / partially implemented requirements
  │        Returns [] if the PR fully satisfies the issue
  │
  ├─► Parse + validate JSON shape (_parse_findings)
  │     └─ Strips markdown code fences, locates JSON array bounds
  │        Drops non-dict items; returns [] on malformed output
  │
  └─► Validate → list[FindingSchema]
        └─ Min confidence 0.6 · drops findings below floor
```

---

## What It Does

| Capability | How |
|---|---|
| Extracts GitHub issue refs | Regex on PR title + body — `#N`, `Closes #N`, `Fixes #N`, `Resolves #N` |
| Fetches issue content | PyGithub installation client — same token as PR review, no extra credentials |
| Detects missing implementation | Claude reads issue description vs. diff and lists unaddressed requirements |
| Graceful degradation | No refs → returns `[]`; provider unavailable → skips silently |

---

## Provider Architecture

The agent uses a `TicketProvider` protocol for extensibility:

```python
class TicketProvider(Protocol):
    def fetch(self, ticket_id: str) -> TicketData | None: ...
```

Current providers:

| Provider | Key | Source |
|---|---|---|
| GitHub Issues | `github_issues` | PyGithub installation client |

Future providers (Jira, Linear, Notion) implement the same protocol and register under their own key in `_build_providers`. Each requires per-org credential storage — not in scope for MVP.

---

## Plan Availability

Runs on `team` and `enterprise` plans only. Gated in `orchestrator/graph.py`.

---

## Output

Each finding is a `FindingSchema` with:
- `agent: "ticket_compliance"`
- `file`, `line_start`, `line_end`, `severity`, `title`, `description`
- `confidence` — model's self-reported certainty the requirement is unmet

---

## Files

```text
specialized/ticket_compliance/
├── __init__.py             — public adapter: analyze(files, diff, pr_payload)
├── agent.py                — main pipeline: extract → fetch → Claude → validate
├── extractor.py            — GitHub issue ref regex
├── schemas.py              — AgentInput dataclass
├── validator.py            — confidence floor filter (≥ 0.6)
├── prompts/
│   └── system.py           — Claude system prompt
└── providers/
    ├── base.py             — TicketData dataclass + TicketProvider protocol
    └── github_issues.py    — GitHubIssuesProvider
```
