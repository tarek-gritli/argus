# Security Agent

Detects security vulnerabilities in pull request diffs by running three deterministic scanners in parallel, then passing pre-annotated results to Claude for exploit reasoning and self-reflection.

---

## Architecture

```text
PR Diff
  │
  ├─► Phase A: Context Builder
  │     └─ System prompt + OWASP Top 10:2025 rules + language-specific SAST rules + repo config
  │
  ├─► Phase B: Parallel Static Scanners (asyncio.gather)
  │     ├─ secret scanner   — Shannon entropy > 3.5 + regex patterns (Stripe, AWS, GitHub, etc.)
  │     ├─ SAST scanner     — regex rules per language (SQL injection, eval, shell=True, etc.)
  │     └─ dep checker      — OSV API (api.osv.dev) with 7-day disk cache; only added/changed deps
  │
  ├─► Phase C: Prompt Assembly
  │     └─ Annotated diff (scanner hits inline) + OWASP schema + output format
  │
  ├─► Phase D: Claude — two calls
  │     ├─ Call 1 (generate)  — exploit reasoning + confidence per annotated line
  │     └─ Call 2 (reflect)   — KEEP / DROP / DOWNGRADE each finding
  │
  └─► Phase E: Output Formatter
        └─ Strip internal fields · assign finding_id UUIDs · validate → list[FindingSchema]
```

---

## What It Does

| Capability | How |
|---|---|
| Detects hardcoded secrets | Entropy check (Shannon > 3.5) + named regex patterns on added lines |
| Detects injection / unsafe code | Regex SAST rules per language (SQL format strings, `eval`, `subprocess shell=True`, etc.) |
| Flags vulnerable dependencies | OSV API querybatch — CVE ID, CVSS score, fix version; 7-day JSON disk cache |
| Reasons about exploit paths | Claude receives pre-annotated diff; does exploit reasoning, not re-detection |
| Filters false positives | Second Claude call acts as skeptical reviewer — drops low-confidence, downgrades inflated severity |

---

## Two-Call Design

**Call 1 (generation):** Claude produces findings with an `exploit_path` reasoning trace and a confidence score. Generation is maximally thorough — no hedging.

**Call 2 (reflection):** A second prompt sends the raw findings back to Claude acting as a skeptical senior reviewer. It applies one of three actions:

| Action | Effect |
|---|---|
| `KEEP` | Finding passes unchanged |
| `DROP` | Finding discarded (unreachable path or confidence < 0.6) |
| `DOWNGRADE` | Severity patched + `revised_severity` set |

Separating generation from reflection produces better results than a single "be critical" instruction — the first call stays thorough, the second has the full list in front of it.

---

## Output

Each finding is a `FindingSchema` with:
- `agent: "security"`
- `file`, `line`, `severity`, `owasp_id`, `category`, `message`
- `suggested_fix` — working code replacement
- `confidence` — post-reflection score

Internal fields (`exploit_path`) are stripped before output.

---

## Files

```text
specialized/security/
├── agent.py           — entry point: all phases, prompts, scanner logic
├── osv_client.py      — OSV API client + 7-day JSON disk cache
├── owasp_fetcher.py   — loads owasp_top10.json + per-language SAST rules
├── schemas.py         — AgentTask, SecurityContext, ScannerHits, RawFinding, Finding, ReviewResult
└── rules/
    ├── owasp_top10.json
    ├── osv_cache.json         — auto-generated disk cache (not committed)
    ├── dependency_cves.json   — static fallback CVE list if OSV is unreachable
    └── sast/
        ├── sast_rules_python.json
        ├── sast_rules_javascript.json
        ├── sast_rules_java.json
        ├── sast_rules_go.json
        ├── sast_rules_kotlin.json
        ├── sast_rules_cpp.json
        ├── sast_rules_csharp.json
        ├── sast_rules_dart.json
        ├── sast_rules_php.json
        └── sast_rules_ruby.json
```
