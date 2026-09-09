# Argus

Multi-agent AI platform that automates code review at the pull-request level.

## Overview

Argus deploys specialized LLM agents in parallel to analyze pull requests, synthesizes findings into actionable feedback, posts inline GitHub review suggestions, and learns from accepted/rejected suggestions over time.

**Active agents (all plans):**
- **Security** — OWASP vulnerability detection, secrets exposure, CVE scanning
- **Quality** — complexity, duplication, dead code, naming
- **Testing** — coverage gaps, weak assertions, test anti-patterns

**Team/Enterprise agents (gated):**
- **Documentation** — PR description generation, docstring completeness
- **Ticket Compliance** — links PR changes to issue tracker requirements, flags scope drift

## Architecture

```
┌──────────────────┐     ┌─────────────┐     ┌──────────────┐
│  GitHub Webhooks │────▶│   Gateway   │────▶│    Celery    │
│  (PR events)     │     │  (FastAPI)  │     │    Queue     │
└──────────────────┘     └─────────────┘     └──────┬───────┘
                                                     │
                                            ┌────────▼────────┐
                                            │  Coordinator    │
                                            │  (orchestrator) │
                                            └────────┬────────┘
                                                     │ LangGraph fan-out
                                   ┌─────────────────┼─────────────────┐
                                   ▼                 ▼                 ▼
                              Security           Quality           Testing
                               Agent             Agent             Agent
                                   └─────────────────┼─────────────────┘
                                                     │
                                            ┌────────▼────────┐
                                            │   Fix Engine    │
                                            │ (gen→val→score) │
                                            └────────┬────────┘
                                                     │
                                            GitHub PR Review + Comment
```

## Packages

- **shared** — SQLAlchemy ORM models, Pydantic schemas, async DB session, Celery queue signatures
- **context** — Qdrant vector embeddings, AST-based chunking, Redis embedding cache
- **integrations** — GitHub App client, PR diff/comment/review posting

## Apps

- **gateway** — FastAPI: webhook validation, org resolution, JWT auth, quota enforcement
- **agents** — LangGraph orchestrator, three parallel review agents, fix engine
- **cli** — Typer CLI: `argus login` (browser OAuth) + `argus review` (local diff review via SSE)
- **web** — Next.js dashboard: marketing site + authed app (reviews, findings, billing, integrations, settings)