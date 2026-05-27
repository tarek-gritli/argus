# Security Agent
### `apps/agents/specialized/security/`

The security agent is the first agent shipped in Argus. It receives a pull request diff, runs three deterministic scanners in parallel, feeds the pre-annotated results to Claude across two separate LLM calls (generate → reflect), and returns a clean structured findings payload to the orchestrator.

This document covers the full end-to-end flow from webhook to output, phase by phase.

---

## Table of Contents

1. [End-to-End Flow (MVP)](#1-end-to-end-flow-mvp)
2. [Phase A — Context Builder](#2-phase-a--context-builder)
3. [Phase B — Parallel Static Scanners](#3-phase-b--parallel-static-scanners)
   - [Secret Scanner](#31-secret-scanner)
   - [SAST Scanner](#32-sast-scanner)
   - [Dep Checker](#33-dep-checker)
4. [Phase C — Prompt Assembly](#4-phase-c--prompt-assembly)
5. [Phase D — Claude Calls](#5-phase-d--claude-calls)
   - [Call 1: Generation](#51-call-1-generation)
   - [Call 2: Self-Reflection](#52-call-2-self-reflection)
   - [Decision Gate](#53-decision-gate)
6. [Phase E — Output Formatter](#6-phase-e--output-formatter)
7. [File & Code Map](#7-file--code-map)
8. [Design Decisions](#8-design-decisions)

---

## 1. End-to-End Flow (MVP)

```
GitHub PR webhook (POST /webhook — PR opened or updated)
        │
        ▼
API Gateway
  · Verify webhook signature (HMAC)
  · Normalize diff → internal format
        │
        ▼
Orchestrator
  · Create review record in PostgreSQL
  · Dispatch Celery task → security agent
        │
        ▼
┌─────────────────────────────────────────────┐
│           security agent (Celery worker)     │
│                                             │
│   Phase A: Context builder                  │
│     System prompt + OWASP rules only        │
│                │                            │
│                ▼                            │
│   Phase B: Parallel scanners                │
│   ┌──────────┐ ┌──────────┐ ┌───────────┐  │
│   │  Secret  │ │   SAST   │ │   Dep     │  │
│   │ scanner  │ │ scanner  │ │ checker   │  │
│   │ entropy  │ │  OWASP   │ │ CVE scan  │  │
│   │ + regex  │ │ patterns │ │ manifests │  │
│   └──────────┘ └──────────┘ └───────────┘  │
│                │                            │
│                ▼                            │
│   Phase C + D: Claude — reason + reflect    │
│     Generate findings → self-reflection     │
│                │                            │
│                ▼                            │
│   Phase E: Validate + format output         │
└─────────────────────────────────────────────┘
        │
        ▼
Orchestrator / review writer
  · Consumes the returned `ReviewResult`
  · Persists findings and marks review "complete"
```

> **Stripped from MVP:** Qdrant vector memory · fix suggestion engine · notification channels · results aggregator (single agent only in Phase 1)

---

## 2. Phase A — Context Builder

The context builder runs first, before any scanning. It configures the agent's "personality" and loads all the static knowledge it will use for the rest of the pipeline.

```
┌──────────────────────────────────────────────────────┐
│                 Phase A — Context Builder             │
│                                                      │
│  ┌─────────────────┐   ┌─────────────────────────┐  │
│  │  System Prompt  │   │      OWASP Rule Set      │  │
│  │                 │   │                          │  │
│  │ Role: security  │   │ Top 10 2025 categories   │  │
│  │   reviewer      │   │ Per-category examples    │  │
│  │ Output: JSON    │   │ Severity mapping table   │  │
│  │   only          │   │ Loaded as static JSON    │  │
│  │ Never flag      │   └─────────────────────────┘  │
│  │   style issues  │                                 │
│  │ Always cite     │   ┌─────────────────────────┐  │
│  │   OWASP         │   │    Language Detector     │  │
│  └─────────────────┘   │                          │  │
│                        │ Infer from file extension│  │
│  ┌─────────────────┐   │ Load lang-specific rules │  │
│  │   Repo Config   │   │ e.g. Python: SQLAlchemy  │  │
│  │  (from PR meta) │   │ e.g. JS: proto pollution │  │
│  │                 │   └─────────────────────────┘  │
│  │ Exempt paths    │                                 │
│  │  (tests/)       │                                 │
│  │ Custom severity │                                 │
│  │  overrides      │                                 │
│  └─────────────────┘                                 │
│                                                      │
│         Assembled context object                     │
│   system_prompt · owasp_rules · lang_rules ·         │
│                  repo_config                         │
│                                                      │
│   passed to → Phase B (scanners) and                 │
│               Phase C (prompt assembly)              │
└──────────────────────────────────────────────────────┘
```

**What it produces:** A `SecurityContext` object containing the system prompt, OWASP rules, language-specific rules inferred from the diff's file extensions, and repo-level config (exempt paths, severity overrides).

---

## 3. Phase B — Parallel Static Scanners

Three pure-code scanners run concurrently via `asyncio.gather` on the raw diff. No LLM is involved. Their job is detection only — Claude receives their output as structured annotations and does exploit reasoning on top of it.

> Total scan time ≈ time of the slowest scanner (usually dep checker). Lines in exempted paths (`tests/`, `fixtures/`) are filtered before scanning.

### 3.1 Secret Scanner

```
Secret scanner
├── Entropy check
│   └── Shannon entropy > 3.5 on added lines only
├── Regex patterns
│   ├── sk_live_           (Stripe live key)
│   ├── AKIA               (AWS access key)
│   ├── ghp_               (GitHub personal token)
│   ├── -----BEGIN RSA     (private key block)
│   └── password\s*=\s*["'] (hardcoded password assignment)
└── Output
    └── file · line · matched_value · pattern_name · entropy
```

### 3.2 SAST Scanner

```
SAST scanner
├── AST parse
│   └── Parse changed lines into syntax tree (tree-sitter per language)
├── Pattern matching
│   ├── SQL format strings (f-string or %-format in SQL context)
│   ├── eval() / exec() calls
│   └── User input flowing to shell command
└── Output
    └── file · line · rule_id · owasp_cat · severity_hint
```

### 3.3 Dep Checker

```
Dep checker
├── Manifest parser
│   ├── requirements.txt
│   ├── package.json
│   ├── pom.xml
│   ├── Gemfile
│   └── go.mod
├── CVE lookup
│   ├── Local NVD mirror (SQLite, ~200MB, updated weekly via CI)
│   ├── Match pkg + version range
│   └── Only new/changed deps are checked
└── Output
    └── pkg · version · cve_id · cvss_score · fix_version
```

**Combined output:** All three scanners produce a merged `ScannerHits` object — an annotated per-line list that is passed directly to Phase C for prompt assembly.

---

## 4. Phase C — Prompt Assembly

The prompt assembler takes the `SecurityContext` from Phase A and the `ScannerHits` from Phase B, and builds the exact string sent to Claude in Call 1.

The annotated diff is the core of the prompt. Each added line from the diff appears alongside its scanner hit inline — so Claude doesn't need to re-detect vulnerabilities, only reason about exploit paths and confidence.

```
[SYSTEM]
You are a security-focused code reviewer. Analyze only
the provided diff. Output a JSON array of findings only.
Never output prose. Never flag style or naming issues.
For every finding cite the OWASP 2021 category.
Severity scale: CRITICAL / HIGH / MEDIUM / LOW / INFO.

OWASP severity mapping (excerpt):
  A01 Broken Access Control      → HIGH-CRITICAL
  A02 Cryptographic Failures     → HIGH-CRITICAL
  A03 Injection                  → HIGH-CRITICAL
  A06 Vulnerable Components      → MEDIUM-HIGH

Language-specific rules (Python):
  - f-string or %-format in SQL → always INJECTION risk
  - subprocess.call(shell=True)  → always COMMAND INJECTION

[USER]
File: src/payments/views.py

Diff (added lines only, with scanner annotations):
  line 12 | + query = f"SELECT * FROM orders WHERE id={order_id}"
           |   [SAST] rule: SQL_FORMAT_STRING  owasp: A03  hint: HIGH
  line 14 | + db.execute(query)
           |   [SAST] taint-sink for line 12
  line 21 | + SECRET_KEY = 'sk_live_9xKp2mQr7vLnT4wZ'
           |   [SECRET] pattern: stripe_live_key  entropy: 4.91  hint: CRITICAL

For each annotated line, produce one finding object in the
schema below. Only include findings for annotated lines.

Schema:
{
  "file": str,
  "line": int,
  "category": str,          // OWASP short name
  "owasp_id": str,          // e.g. "A03:2021"
  "severity": str,
  "exploit_path": str,      // 1 sentence, concrete (internal use only)
  "message": str,           // human-readable, ≤ 2 sentences
  "suggested_fix": str,     // working code replacement
  "confidence": float       // 0.0 – 1.0
}
```

---

## 5. Phase D — Claude Calls

### 5.1 Call 1: Generation

Claude receives the assembled prompt and returns a raw JSON array. Confidence scores at this stage are Claude's own self-assessment — they haven't been validated yet. The `exploit_path` field is internal: it is used by the reflection prompt and then stripped from the final output.

```json
[
  {
    "file": "src/payments/views.py",
    "line": 12,
    "category": "SQL Injection",
    "owasp_id": "A03:2021",
    "severity": "HIGH",
    "exploit_path": "Attacker passes order_id=1 OR 1=1-- to dump all orders without auth.",
    "message": "f-string formatting passes order_id directly into a raw SQL query with no parameterization. Any user-controlled value in order_id enables classic SQL injection.",
    "suggested_fix": "cursor.execute('SELECT * FROM orders WHERE id = %s', (order_id,))",
    "confidence": 0.97
  },
  {
    "file": "src/payments/views.py",
    "line": 21,
    "category": "Hardcoded Secret",
    "owasp_id": "A02:2021",
    "severity": "CRITICAL",
    "exploit_path": "Live Stripe key checked into source. Any repo reader can make charges or exfiltrate customer payment data.",
    "message": "Live Stripe secret key is hardcoded in source. This key grants full Stripe API access.",
    "suggested_fix": "SECRET_KEY = os.environ['STRIPE_SECRET_KEY']",
    "confidence": 0.99
  }
]
```

### 5.2 Call 2: Self-Reflection

A second, shorter Claude call sends the raw findings back with a different system prompt: act as a skeptical senior security engineer. It checks three things per finding:

1. Is the exploit path realistically reachable?
2. Is the severity proportionate to actual risk?
3. Is confidence ≥ 0.6?

```
[SYSTEM — reflection call]
You are a skeptical senior security engineer reviewing
AI-generated findings. For each finding ask:
  1. Is this exploit realistically reachable?
  2. Is the severity proportionate to actual risk?
  3. Is confidence >= 0.6?
If all three pass → output the finding unchanged.
If confidence < 0.6 → set action: "DROP".
If severity is inflated → set action: "DOWNGRADE" + reason.

[USER]
Review these findings: [... raw findings from call 1 ...]

[CLAUDE RESPONSE]
[
  { "finding_index": 0, "action": "KEEP",
    "reason": "SQL injection via format string is a direct, exploitable path. Confidence 0.97 is warranted." },
  { "finding_index": 1, "action": "KEEP",
    "reason": "Hardcoded live key is unambiguous. Severity CRITICAL correct." }
]
```

### 5.3 Decision Gate

The reflection output is applied programmatically — no more LLM calls.

| Action | Effect |
|---|---|
| `KEEP` | Finding passes unchanged |
| `DROP` | Finding is discarded entirely |
| `DOWNGRADE` | Severity field is patched; `downgrade_reason` annotation is added |

Only findings that survive move to Phase E.

```
# Example DROP:
Action on idx 2: DROP
  reason: "This eval() is inside a test helper with no user-controlled
           input. Exploit path is not realistically reachable."
→ Finding discarded.

# Example DOWNGRADE:
Action on idx 1: DOWNGRADE
  original severity: CRITICAL
  revised severity:  HIGH
  reason: "Endpoint is internal-only, behind mTLS. Attack surface is
           limited to internal services only."
→ Finding kept, severity patched to HIGH.
```

---

### 6. Phase E — Validation + Output Formatter

The validator and formatter strip all internal fields (`exploit_path`, `downgrade_reason`, `action`) that were only used during reasoning. They validate every field against the output schema using Pydantic, assign a unique `finding_id` (UUID), and emit the clean array to the orchestrator.

```json
{
  "review_id": "rev-f3a1b",
  "pr_number": 412,
  "repo": "org/payment-service",
  "agent": "security",
  "created_at": "2026-03-28T14:22:01Z",
  "findings": [
    {
      "finding_id": "a1b2c3d4-...",
      "agent_id": "security",
      "file": "src/payments/views.py",
      "line": 12,
      "severity": "HIGH",
      "owasp_id": "A03:2021",
      "category": "SQL Injection",
      "message": "f-string formatting passes order_id directly into a raw SQL query.",
      "suggested_fix": "cursor.execute('SELECT * FROM orders WHERE id = %s', (order_id,))",
      "confidence": 0.97
    },
    {
      "finding_id": "e5f6g7h8-...",
      "agent_id": "security",
      "file": "src/payments/views.py",
      "line": 21,
      "severity": "CRITICAL",
      "owasp_id": "A02:2021",
      "category": "Hardcoded Secret",
      "message": "Live Stripe secret key is hardcoded in source. Full API access exposed.",
      "suggested_fix": "SECRET_KEY = os.environ['STRIPE_SECRET_KEY']",
      "confidence": 0.99
    }
  ]
}
```

---

## 7. File & Code Map

```
apps/agents/specialized/security/
├── agent.py                  ← entry point
├── schemas.py                ← Pydantic types
├── validator.py              ← confidence policy + fallback reflection
├── tools/
│   ├── secret_scanner.py     ← scanner
│   ├── sast_scanner.py       ← scanner
│   └── dep_checker.py        ← scanner
└── rules/                    ← static data
    ├── owasp_top10.json
    ├── sast_rules_python.json
    ├── sast_rules_javascript.json
    ├── secret_patterns.json
    └── nvd_mirror.db
```

### `agent.py` — Entry Point

| Function | Signature | Description |
|---|---|---|
| `run_security_agent` | `(task: AgentTask) → List[Finding]` | Celery task entry. Orchestrates A→B→C→D→E in order. Handles timeout and error logging. |
| `_build_context` | `(task) → SecurityContext` | Phase A. Loads system prompt, OWASP rules JSON, detects language from file extensions in diff. |
| `_run_scanners` | `(diff, ctx) → ScannerHits` | Phase B. Runs all three scanners concurrently via `asyncio.gather`. Filters exempt paths. |
| `_assemble_prompt` | `(diff, hits, ctx) → str` | Phase C. Builds the final prompt string: system block + annotated diff + schema instruction. |
| `_call_claude_generate` | `(prompt) → List[RawFinding]` | Phase D call 1. Sends prompt to Claude, parses JSON response, validates against `RawFinding` schema. |
| `_call_claude_reflect` | `(raw: List[RawFinding]) → List[Finding]` | Phase D call 2. Sends raw findings to reflection prompt. Applies KEEP / DROP / DOWNGRADE decisions. |
| `_format_output` | `(findings, task) → ReviewResult` | Phase E. Strips internal fields, assigns `finding_id` UUIDs, validates with Pydantic, returns final object. |

### `tools/secret_scanner.py`

| Symbol | Description |
|---|---|
| `scan(diff_lines)` | Iterates added lines only. Runs entropy check (Shannon > 3.5) then regex pattern list. Returns hits with `matched_value`, `pattern_name`, `entropy`. |
| `_shannon_entropy(s)` | Values above 3.5 on tokens ≥ 20 chars trigger a hit. |
| `PATTERNS` | Compiled regex list: `stripe sk_live_`, `AWS AKIA`, `GitHub ghp_`, generic `password=` assignment, `BEGIN RSA PRIVATE KEY`, etc. |

### `tools/sast_scanner.py`

| Symbol | Description |
|---|---|
| `scan(diff_lines, language)` | Parses changed lines into AST (tree-sitter per language). Runs rule matchers against the tree. Returns hits with `rule_id`, `owasp_cat`, `severity_hint`. |
| `RULES` | Keyed by language. Python: SQL format strings, `subprocess shell=True`, `eval`/`exec`, `pickle.loads` on user input. JS: `innerHTML` assignment, prototype pollution, `eval`. |

### `tools/dep_checker.py`

| Symbol | Description |
|---|---|
| `scan(diff_lines)` | Extracts added dependency lines from manifest files in diff. Looks up each `pkg+version` against local NVD mirror. Returns hits with `cve_id`, `cvss_score`, `fix_version`. |
| `_parse_manifests(lines)` | Handles `requirements.txt`, `package.json`, `pom.xml`, `Gemfile`, `go.mod`. Returns normalized `(name, version)` tuples. |

### `agent.py` prompt helpers

| Symbol | Description |
|---|---|
| `SYSTEM_PROMPT` | Security reviewer persona. JSON-only output, OWASP citation, no style findings. |
| `REFLECTION_PROMPT` | Skeptical senior reviewer persona. Defines DROP / KEEP / DOWNGRADE actions and when to apply each. |
| `_build_generation_prompt(diff, hits, ctx)` | Assembles user-turn string: annotated diff lines + schema definition + instructions. |
| `_build_reflection_prompt(raw_findings)` | Serializes raw findings into the reflection user-turn. |

### `schemas.py`

| Type | Fields |
|---|---|
| `AgentTask` | `diff`, `pr_number`, `repo_id`, `repo_config` |
| `SecurityContext` | `system_prompt`, `owasp_rules`, `lang_rules`, `exempt_paths` |
| `ScannerHits` | `secrets: List[SecretHit]`, `sast: List[SASTHit]`, `deps: List[DepHit]` |
| `RawFinding` | All fields including `exploit_path` (internal only — never written to storage) |
| `Finding` | Public schema: no internal fields, `finding_id` assigned |
| `ReviewResult` | `review_id`, `pr_number`, `repo`, `agent`, `created_at`, `findings` |

### `rules/` — Static Data

| File | Contents |
|---|---|
| `owasp_top10.json` | Category definitions + severity mapping table |
| `sast_rules_python.json` | tree-sitter patterns for Python |
| `sast_rules_javascript.json` | tree-sitter patterns for JS/TS |
| `secret_patterns.json` | Compiled regex list with names and severity hints |
| `nvd_mirror.db` | SQLite snapshot of NVD CVE data (~200MB compressed), updated weekly via CI job (`nvd_sync.py`) |

---

## 8. Design Decisions

### Why two Claude calls instead of one with a "be critical" instruction

A single prompt that says "generate findings but also be skeptical" produces findings that are already watered-down — Claude hedges during generation. Separating generation from reflection means the first call is maximally thorough, and the second call has the full list in front of it to make real drop/downgrade decisions. The cost difference is small since the reflection call is short.

### Why scanners run before Claude and not after

If you sent the raw diff to Claude and asked it to detect everything, it would miss many issues and hallucinate others. The scanners are deterministic and cheap — they give Claude a pre-annotated diff where it only needs to do exploit reasoning, not detection. This is the key quality lever.

### The `exploit_path` field

`exploit_path` is the internal reasoning trace Claude writes to justify its confidence score. It never leaves the agent — the formatter strips it before writing to S3. But it is essential for the reflection call because the reflection prompt reads it to decide if the path is realistic.

### The `nvd_mirror.db` update cycle

`nvd_mirror.db` is a SQLite file (~200MB compressed) that ships inside the Docker image — no network call at scan time. A weekly CI job runs `nvd_sync.py`, rebuilds the SQLite, and pushes a new image tag. If the CI job fails, the agent continues to run against the previous mirror and emits a warning log.

### Auto-apply constraint

Auto-apply of suggested fixes is gated at **confidence > 0.90** and **single-file changes only**. Multi-file and low-confidence fixes always surface for human approval.

---

*v1.1 — Security Agent | Argus · Confidential*
