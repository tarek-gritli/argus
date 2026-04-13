# ARGUS — Authoritative Project Context

> Read this entire file before touching any code.
> When in doubt about where something goes or what's allowed, the answer is here.
> This file overrides any conflicting information elsewhere in the codebase.

---

## What Argus Is

Multi-agent AI platform that automates code review at the pull-request level.
Deploys specialized agents in parallel, synthesizes findings into actionable feedback,
and learns from accepted/rejected suggestions over time.

**Current build phase: Phase 1**
- API gateway + GitHub webhook handler
- Orchestrator with one agent (Security) — full loop end-to-end only
- No auth, no billing, no multi-tenancy, no CLI, no dashboard yet

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
│   ├── cli/            # Typer CLI (Phase 7 — do not build)
│   └── web/            # Next.js dashboard (Phase 6 — do not build)
├── packages/
│   ├── shared/         # Cross-app models, schemas, DB session, queue interface
│   ├── context/        # Vector embeddings + dependency graph (Phase 5 — do not build)
│   └── integrations/   # GitHub/GitLab/Slack/Notion API clients
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
├── main.py                  # FastAPI app init, router registration, lifespan hooks
├── routers/
│   ├── webhooks.py          # POST /api/v1/webhooks/github — ONLY active route in Phase 1
│   ├── reviews.py           # Review endpoints (Phase 2 — stub only)
│   └── auth.py              # OAuth routes (Phase 3 — stub only)
├── middleware/
│   ├── auth.py              # JWT validation (Phase 3 — stub, do nothing)
│   ├── rate_limit.py        # Redis rate limiter (Phase 3 — stub, do nothing)
│   └── quota.py             # Quota enforcement (Phase 3 — stub, do nothing)
└── schemas/
    └── github.py            # Pydantic models for GitHub webhook payloads
```

### The only active route in Phase 1:

```
POST /api/v1/webhooks/github
  1. Validate X-Hub-Signature-256 HMAC-SHA256 — 403 if invalid
  2. Filter: only pull_request events with action in [opened, synchronize, reopened]
     → Return 200 immediately and do nothing for all other events
  3. Deduplicate on X-GitHub-Delivery header via Redis — discard if already seen
  4. Extract: action, repo_full_name, pr_number, head_sha, base_sha, installation_id
  5. Enqueue Celery task: review_pr(payload)
  6. Return 200 — no further processing in the handler
```

---

## apps/agents — Sole Responsibility

**All AI execution. Orchestration, agent dispatch, fix generation.**

Agents never handle HTTP. They receive tasks from Celery only.

```
apps/agents/
├── main.py                  # Celery worker entrypoint
├── orchestrator/
│   ├── graph.py             # LangGraph graph: nodes, edges, shared state definition
│   ├── coordinator.py       # Receives Celery task → builds graph → triggers execution
│   ├── conflict.py          # Conflict resolution when agents disagree (Phase 3)
│   └── __init__.py
├── specialized/
│   ├── security.py          # Security agent — ONLY active agent in Phase 1
│   ├── quality.py           # (Phase 3 — stub only)
│   ├── best_practices.py    # (Phase 3 — stub only)
│   ├── performance.py       # (Phase 3 — stub only)
│   ├── testing.py           # (Phase 3 — stub only)
│   ├── documentation.py     # (Phase 3 — stub only)
│   └── ticket_compliance.py # (Phase 3 — stub only)
├── fix_engine/
│   ├── generator.py         # Generate code patches (Phase 2 — stub only)
│   ├── validator.py         # Sandbox-test patches (Phase 2 — stub only)
│   ├── scorer.py            # Confidence scoring (Phase 2 — stub only)
│   └── __init__.py
└── workers/
    └── celery_app.py        # Celery app instance + task: review_pr
```

### Agent internal pipeline (every agent must follow this exactly):
1. **Input** — receive diff + file context + repo metadata
2. **Context injection** — vector embeddings + historical findings (Phase 5, skip for now)
3. **LLM analysis** — Claude performs domain-specific review via LangGraph node
4. **Self-validation** — agent checks its own output, filters false positives
5. **Output** — structured FindingSchema JSON, nothing else

### Phase 1 agent scope:
- Only `security.py` runs
- `coordinator.py` receives the Celery task, invokes security agent, posts findings to GitHub PR as inline comments
- Fix engine is stubbed — do not implement

---

## apps/cli — Sole Responsibility

**Developer-facing local review tool. Phase 7 — do not build, do not add logic.**

```
apps/cli/
├── main.py              # Typer entrypoint — stub
└── commands/
    ├── review.py        # argus review [files]
    ├── fix.py           # argus fix [files] --auto
    ├── watch.py         # argus watch
    └── baseline.py      # argus baseline
```

---

## apps/web — Sole Responsibility

**Next.js dashboard. Phase 6 — do not build, do not add logic.**
Scaffold exists. Leave it alone until Phase 6.

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
│   ├── pr.py        # fetch_pr_diff(), post_review_comment(), post_finding()
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

**Semantic context retrieval. Phase 5 — do not build.**

```
packages/context/context/
├── embeddings.py    # Embed code chunks → Qdrant
├── cache.py         # Redis cache for embeddings
└── graph.py         # Neo4j dependency graph queries
```

---

## Canonical Data Contract

Every agent outputs FindingSchema. No exceptions. No custom formats.

```python
# packages/shared/shared/schemas/finding.py
class FindingSchema(BaseModel):
    agent: str           # "security" | "quality" | "performance" | etc.
    severity: str        # "critical" | "high" | "medium" | "low" | "info"
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

# Postgres
DATABASE_URL=postgresql+asyncpg://argus:argus@localhost:5432/argus

# Redis
REDIS_URL=redis://localhost:6379/0

# Celery
CELERY_BROKER_URL=redis://localhost:6379/1

# LLM
ANTHROPIC_API_KEY=

# App
ENV=development
```

---

## What Is NOT Built Yet — Do Not Implement

| Feature | Phase |
|---|---|
| JWT auth / API keys | 3 |
| Multi-tenancy / RBAC | 3 |
| Billing / quota enforcement | 3 |
| GitLab integration | 2 |
| Fix engine | 2 |
| Agents beyond Security | 3 |
| Qdrant context injection | 5 |
| Neo4j dependency graph | 5 |
| CLI commands | 7 |
| Web dashboard | 6 |

Stubs are allowed. Implementation is not.

---

## Absolute Rules

1. **Gateway never contains business logic** — validate, filter, enqueue, return 200
2. **Agents never handle HTTP** — Celery tasks only, never FastAPI routes
3. **shared package has no app-specific imports** — no gateway, no agent code
4. **Every agent outputs FindingSchema** — no exceptions
5. **Private key never read from file at runtime** — base64 env var, loaded lazily via get_settings()
6. **No processing inside the webhook handler** — enqueue and return, nothing else
7. **Middleware stubs do nothing in Phase 1** — do not activate prematurely
8. **uv only for Python deps** — never suggest pip install
9. **Do not add dependencies without checking if they are already in the workspace**