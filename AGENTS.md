# ARGUS — Authoritative Project Context

> Read this entire file before touching any code.
> When in doubt about where something goes or what's allowed, the answer is here.
> This file overrides any conflicting information elsewhere in the codebase.

---

## Coding Behavior Guidelines

### 1. Think Before Coding
**Don't assume. Don't hide confusion. Surface tradeoffs.**

Before implementing:
- State your assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them — don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what's confusing. Ask.

### 2. Simplicity First
**Minimum code that solves the problem. Nothing speculative.**

- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" or "configurability" that wasn't requested.
- No error handling for impossible scenarios.
- If you write 200 lines and it could be 50, rewrite it.

Ask yourself: "Would a senior engineer say this is overcomplicated?" If yes, simplify.

### 3. Surgical Changes
**Touch only what you must. Clean up only your own mess.**

When editing existing code:
- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- If you notice unrelated dead code, mention it — don't delete it.

When your changes create orphans:
- Remove imports/variables/functions that YOUR changes made unused.
- Don't remove pre-existing dead code unless asked.

The test: Every changed line should trace directly to the user's request.

### 4. Goal-Driven Execution
**Define success criteria. Loop until verified.**

Transform tasks into verifiable goals:
- "Add validation" → "Write tests for invalid inputs, then make them pass"
- "Fix the bug" → "Write a test that reproduces it, then make it pass"
- "Refactor X" → "Ensure tests pass before and after"

For multi-step tasks, state a brief plan:
\```
1. [Step] → verify: [check]
2. [Step] → verify: [check]
3. [Step] → verify: [check]
\```

## What Argus Is

Multi-agent AI platform that automates code review at the pull-request level.
Deploys specialized agents in parallel, synthesizes findings into actionable feedback,
and learns from accepted/rejected suggestions over time.

**Current build phase: Phase 6 (Web dashboard) — in progress**
- API gateway + GitHub webhook handler ✅
- Orchestrator with three parallel agents (Security, Quality, Testing) — full loop end-to-end ✅
- Fix engine (generator → validator → scorer → pipeline) ✅
- Inline GitHub review suggestions (`post_findings_as_review`) ✅
- JWT auth + GitHub OAuth ✅
- Multi-org via `UserOrg` join table ✅
- Billing + quota enforcement (free/pro/team/enterprise) ✅
- Review API (`GET /api/v1/reviews/`) ✅
- Semantic context injection via Qdrant + Voyage AI ✅
- AST-based code chunking (9 languages) ✅
- Blue-green Qdrant collection swap for zero-downtime reindex ✅
- CLI `argus login` + `argus review` — browser OAuth flow + async local review via SSE ✅
- Next.js dashboard — marketing site + authed dashboard (reviews, findings, billing, integrations, settings) ✅

---

## Tooling Rules (Non-Negotiable)

- **Python package manager: `uv` only** — never pip, poetry, or pdm
- **Linter: ruff only** — `select = ["E", "F", "I"]` — never black, flake8, pylint
- **Frontend package manager: pnpm only** — only inside `apps/web/`, never touch from root
- **Python version: 3.12**

```bash
uv sync --all-packages         # Install all workspace members
uv run ruff check .            # Lint
uv run ruff check --fix .      # Fix lint
uv run ruff format .           # Format
uv run pytest tests/           # All tests
```

Adding dependencies:
```bash
uv add --package gateway httpx          # External dep to specific app
uv add --package gateway shared   # Internal workspace dep
uv add --package shared sqlalchemy      # External dep to shared package
```

---

## Developer Commands

```bash
# Services
make run-gateway        # FastAPI gateway (uvicorn)
make run-agents         # Celery workers
make run-cli            # CLI entrypoint

# Code quality
make lint               # ruff check
make fix                # ruff check --fix
make fmt                # ruff format

# Database
make migrate NAME="description"   # Create new Alembic migration
make migrate-up                   # Apply migrations
make migrate-down                 # Rollback one step

# Tests
make test               # All tests
make test-unit          # tests/unit/ only
make test-integration   # tests/integration/ only

# Web (runs separately)
cd apps/web && pnpm install
cd apps/web && pnpm dev
```

---

## Monorepo Layout

```
argus/
├── apps/
│   ├── gateway/        # FastAPI — ONLY public-facing HTTP service
│   ├── agents/         # All AI execution: orchestration, agents, fix engine
│   ├── cli/            # Typer CLI — login + review commands active ✅
│   └── web/            # Next.js dashboard — marketing site + authed dashboard ✅
├── packages/
│   ├── shared/         # Cross-app models, schemas, DB session, queue interface
│   ├── context/        # Vector embeddings (Qdrant), AST chunking, Redis cache ✅
│   └── integrations/   # GitHub App client, GitLab stub
├── migrations/         # Alembic migrations — models live in packages/shared
├── tests/
│   ├── unit/
│   ├── integration/
│   └── e2e/
├── infra/              # Kubernetes + Terraform (do not touch in Phase 1)
└── docker-compose.yml  # Local dev stack: PostgreSQL, Redis, Qdrant
```

---

## apps/gateway — Sole Responsibility

**Receives external HTTP requests, validates them, enqueues work, returns 200. Nothing else.**

It does NOT contain business logic.
It does NOT call the LLM.
It does NOT query the database directly.
It does NOT process findings.

```
apps/gateway/
├── gateway_main.py          # FastAPI app init, router registration, lifespan hooks
├── auth_utils.py            # JWT decode helpers
├── org_resolver.py          # Org resolution from JWT claims
├── api/
│   ├── __init__.py          # api_router — aggregates all sub-routers
│   └── routes/
│       ├── webhooks.py      # POST /api/v1/webhooks/github — GitHub PR webhook
│       ├── stripe_webhooks.py # POST /api/v1/webhooks/stripe — Stripe events
│       ├── auth.py          # JWT auth endpoints
│       ├── auth_cli.py      # CLI session: POST /session, GET /token/{session_id}
│       ├── oauth.py         # GitHub OAuth callback
│       ├── reviews.py       # GET /api/v1/reviews/
│       ├── reviews_local.py # POST/GET/SSE /api/v1/reviews/local — async local review
│       ├── billing.py       # Billing + quota endpoints
│       ├── integrations.py  # Integration management
│       ├── admin.py         # Admin endpoints
│       └── dashboard.py     # Dashboard data endpoints
└── middleware/
    ├── auth.py              # JWT validation middleware — active ✅
    ├── rate_limit.py        # Redis rate limiter — active ✅
    └── quota.py             # Quota enforcement — active ✅
```

### Active routes (summary):

```
POST /api/v1/webhooks/github     — validate HMAC, filter PR events, enqueue review_pr
POST /api/v1/webhooks/stripe     — handle Stripe billing events
POST /api/v1/auth/cli/session    — create CLI login session, return session_id + browser_url
GET  /api/v1/auth/cli/token/{id} — poll for JWT after browser OAuth completes (atomic GETDEL)
GET  /api/v1/reviews/            — list reviews for authenticated org
POST /api/v1/reviews/local       — enqueue local diff review, return job_id
GET  /api/v1/reviews/local/{id}  — poll local review status/findings
GET  /api/v1/reviews/local/{id}/stream — SSE stream of findings as agents complete
```

---

## apps/agents — Sole Responsibility

**All AI execution. Orchestration, agent dispatch, fix generation.**

Agents never handle HTTP. They receive tasks from Celery only.

```
apps/agents/
├── main.py                  # Celery worker entrypoint
├── orchestrator/
│   ├── graph.py             # LangGraph graph: parallel fan-out to agents
│   ├── coordinator.py       # Receives Celery task → fetches diff + context → triggers graph → posts review
│   ├── quota.py             # Quota check + increment helpers
│   └── __init__.py
├── specialized/
│   ├── security/            # Security agent — active (OWASP, secrets, CVE)
│   │   ├── agent.py
│   │   ├── schemas.py
│   │   ├── osv_client.py
│   │   ├── owasp_fetcher.py
│   │   └── rules/
│   ├── quality/             # Quality agent — active (complexity, duplication, dead code)
│   │   ├── agent.py
│   │   ├── schemas.py
│   │   ├── checks/
│   │   ├── prompts/
│   │   ├── tools/
│   │   └── validator.py
│   ├── testing/             # Testing agent — active (coverage gaps, weak assertions)
│   │   ├── agent.py
│   │   ├── schemas.py
│   │   ├── prompts/
│   │   ├── tools/
│   │   └── validator.py
│   ├── documentation/       # Documentation agent — team/enterprise only
│   │   ├── agent.py
│   │   ├── pr_description.py
│   │   └── ...
│   └── ticket_compliance/   # Ticket compliance agent — team/enterprise only ✅
├── fix_engine/
│   ├── generator.py         # Generate code patches via Claude ✅
│   ├── validator.py         # Multi-language patch validation ✅
│   ├── scorer.py            # Confidence scoring ✅
│   ├── pipeline.py          # Orchestrates generator → validator → scorer ✅
│   ├── prompts.py           # System prompt for fix generation ✅
│   ├── schemas.py           # FixProposal, ValidationResult ✅
│   └── __init__.py
└── workers/
    ├── celery_app.py        # Celery app instance + tasks: review_pr, index_repo, review_local
    ├── connections.py       # Shared Redis/Qdrant connection helpers for workers
    ├── index_task.py        # Repo indexing task (embeds code → Qdrant)
    └── local_review_task.py # Local diff review task — runs agents, publishes findings to Redis pub/sub
```

### Agent internal pipeline (every agent must follow this exactly):
1. **Input** — receive diff + file context + repo metadata
2. **Context injection** — vector embeddings + historical findings (via `packages/context` ✅)
3. **LLM analysis** — Claude performs domain-specific review via LangGraph node
4. **Self-validation** — agent checks its own output, filters false positives
5. **Output** — structured FindingSchema JSON, nothing else

### Phase 2 agent scope:
- **Security** (`specialized/security/`) — OWASP analysis, secret detection, dependency CVE scan
- **Quality** (`specialized/quality/`) — complexity, duplication, dead code, naming
- **Testing** (`specialized/testing/`) — coverage gaps, weak assertions, test anti-patterns
- All three run in parallel via LangGraph fan-out; findings are merged by a reducer and posted as inline GitHub review suggestions + a summary issue comment grouped by agent, then by severity
- `coordinator.py` fetches the PR diff via `get_pr_diff()`, builds `AgentInput` for quality and testing adapters, passes `files` + `PullRequestPayload` to the security adapter
- Fix engine runs after agents complete: generates patches via Claude, validates (multi-language), scores by severity + churn, attaches `FixSchema` to qualifying findings
- Fixes are posted as native GitHub `suggestion` blocks via `post_findings_as_review()`

---

## apps/cli — Sole Responsibility

**Developer-facing local review tool. `login` and `review` commands are active.**

```
apps/cli/
├── main.py              # Typer entrypoint — registers login + review commands
├── auth.py              # Token persistence (~/.config/argus/credentials.json, 0o600)
├── client.py            # httpx.Client factory (Bearer token, 120s timeout)
└── commands/
    ├── login.py         # argus login — browser OAuth flow via CLI session API ✅
    └── review.py        # argus review [files] — async local review, SSE + polling fallback ✅
```

The binary is built with PyInstaller (`argus.spec`) and distributed via GitHub Releases + `install.sh`.

---

## apps/web — Sole Responsibility

**Next.js dashboard. Renders data from the gateway API — no business logic, no direct DB/LLM access.**

Next.js 16 (App Router, React 19, React Compiler), Tailwind v4, shadcn, TanStack Query + Table, Zod.
**pnpm only**, run from inside `apps/web/`.

```
apps/web/
├── app/
│   ├── (marketing)/        # Public landing site (hero, bento, pricing, FAQ, testimonials)
│   ├── login/              # GitHub OAuth entry
│   ├── auth/callback/      # OAuth return → posts code to /api/auth/set-token
│   ├── api/auth/set-token/ # Route handler — sets httpOnly argus_token cookie (CSRF: origin + one-time nonce)
│   └── dashboard/
│       ├── page.tsx        # Stats strip + recent reviews
│       ├── reviews/        # List + [id] detail with findings explorer (accept/reject)
│       ├── billing/        # Plan card, quota bars, upgrade dialog, Stripe success/cancel
│       ├── integrations/   # Integration cards, Notion database picker (team/enterprise)
│       └── settings/       # Org + team member details
├── components/             # sidebar, topbar, auth-guard, providers, ui/ (shadcn primitives)
├── lib/
│   ├── api.ts              # Typed fetch client → gateway (credentials: include)
│   ├── queries.ts          # TanStack Query options + mutation hooks
│   ├── types.ts            # Zod schemas for API responses
│   └── auth.ts             # Reads non-sensitive argus_authed / argus_org_id cookies
├── proxy.ts                # Middleware — redirects unauthed to /login, authed away from /login
└── next.config.ts          # Rewrites /api/* → GATEWAY_URL (server-side proxy, avoids cross-origin cookie issues)
```

Env: `NEXT_PUBLIC_API_URL`, `GATEWAY_URL` (required in non-dev), `FRONTEND_URL`.

Gateway routes the dashboard consumes (beyond the summary above):
```
GET    /api/v1/reviews/{id}                              — review detail
GET    /api/v1/reviews/{id}/findings                     — findings, filter by severity/agent
POST   /api/v1/reviews/{id}/findings/{fid}/accept|reject — feedback signal for history suppression
GET    /api/v1/billing/  ·  POST /api/v1/billing/checkout|portal
GET    /api/v1/orgs/{org_id}/integrations  ·  PATCH/DELETE .../{integration_id}
GET    /api/v1/orgs/{org_id}/integrations/{id}/notion/databases  ·  PATCH .../notion/database
GET    /api/v1/oauth/{kind}/authorize  ·  DELETE /api/v1/auth/logout  ·  GET /api/v1/auth/github/login
```

---

## packages/shared — Sole Responsibility

**Everything multiple apps import. Single source of truth for data contracts.**

```
packages/shared/shared/
├── models/          # SQLAlchemy ORM models: Repo, Review, Finding, Fix, Tenant
├── schemas/         # Pydantic schemas used across apps
│   ├── finding.py   # FindingSchema — canonical agent output format
│   └── review.py    # ReviewSchema
├── db/              # SQLAlchemy async engine + session factory
└── queue/           # Celery task signatures only (not the worker itself)
```

Rules:
- No app-specific logic
- No HTTP code
- No LLM calls
- If only one app uses it, it does not belong here

---

## packages/integrations — Sole Responsibility

**All external API clients.**

```
packages/integrations/integrations/
├── github/
│   ├── client.py    # get_installation_client(installation_id) → Github
│   ├── pr.py        # get_pr_diff(), post_issue_comment(), post_findings_as_review()
│   └── webhook.py   # validate_signature(payload, signature, secret) → bool
└── gitlab/
    └── __init__.py  # Phase 2 — stub only
```

GitHub client rules:
- Private key loaded lazily via `get_settings()` (lru_cache) from GITHUB_PRIVATE_KEY_B64 env var (base64 string)
- Installation tokens cached in-memory with TTL — tokens last 3600s, refresh 60s before expiry
- Never read from .pem file at request time
- Use `Auth.AppAuth(app_id, private_key)` with `GithubIntegration(auth=…)` to get access tokens
- Never use the deprecated old-style arguments: `GithubIntegration(integration_id=…, private_key=…, …)`

---

## packages/context — Sole Responsibility

**Semantic context retrieval. Phase 4 — complete.**

```
packages/context/context/
├── chunker.py       # AST-based code splitting (tree-sitter, 9 languages)
├── embeddings.py    # Voyage AI → Qdrant; blue-green collection swap
├── cache.py         # Redis TTL cache for embedding lookups
├── bundle.py        # ContextBundle passed read-only to agents
└── history.py       # Rejected finding suppression
```
---

## Canonical Data Contract

Every agent outputs FindingSchema. No exceptions. No custom formats.

```python
# packages/shared/shared/schemas/finding.py
# AgentType = Literal["security", "quality", "testing", "documentation", "ticket_compliance"]
# SeverityType = Literal["critical", "high", "medium", "low", "info"]
class FindingSchema(BaseModel):
    agent: AgentType     # see AgentType literal above
    severity: SeverityType
    file: str            # repo-relative file path
    line_start: int
    line_end: int
    title: str
    description: str
    suggestion: str | None
    confidence: float    # 0.0-1.0
    fix: FixSchema | None
```

---

## Environment Variables

```bash
# GitHub App
GITHUB_APP_ID=
GITHUB_WEBHOOK_SECRET=
GITHUB_PRIVATE_KEY_B64=      # base64 of .pem: cat key.pem | base64 | tr -d '\n'

# GitHub OAuth
GITHUB_CLIENT_ID=
GITHUB_CLIENT_SECRET=

# JWT
JWT_SECRET_KEY=
JWT_TTL_SECONDS=86400

# Postgres
DATABASE_URL=postgresql+asyncpg://argus:argus@localhost:5432/argus

# Redis
REDIS_URL=redis://localhost:6379/0

# Celery
CELERY_BROKER_URL=redis://localhost:6379/1

# LLM
ANTHROPIC_API_KEY=

# Qdrant (vector embeddings)
QDRANT_URL=http://localhost:6333
QDRANT_API_KEY=              # empty for local dev

# Voyage AI (code embeddings)
VOYAGE_API_KEY=

# App
ENV=development
```

---

## What Is NOT Built Yet — Do Not Implement

| Feature | Phase | Status |
|---|---|---|
| JWT auth + GitHub OAuth | 3 | ✅ complete |
| Multi-org / RBAC | 3 | ✅ complete |
| Billing / quota enforcement | 3 | ✅ complete |
| Fix engine | 3 | ✅ complete |
| Inline GitHub review suggestions | 3 | ✅ complete |
| Qdrant context injection | 4 | ✅ complete |
| AST-based chunking (9 languages) | 4 | ✅ complete |
| Documentation agent (team/enterprise) | 3 | ✅ active |
| Ticket compliance agent | 3 | ✅ active |
| CLI login + review commands | 5 | ✅ complete |
| Web dashboard (marketing + authed app) | 6 | ✅ in progress |
| GitLab integration | — | stub only |

Stubs are allowed. Implementation is not.

---

## Absolute Rules

1. **Gateway never contains business logic** — validate, filter, enqueue, return 200
2. **Agents never handle HTTP** — Celery tasks only, never FastAPI routes
3. **shared package has no app-specific imports** — no gateway, no agent code
4. **Every agent outputs FindingSchema** — no exceptions
5. **Private key never read from file at runtime** — base64 env var, loaded lazily via get_settings()
6. **No processing inside the webhook handler** — enqueue and return, nothing else
7. **Middleware is active** — `AuthMiddleware` and `RateLimitMiddleware` are registered in `gateway_main.py`; do not disable or bypass them
8. **uv only for Python deps** — never suggest pip install
9. **Do not add dependencies without checking if they are already in the workspace**