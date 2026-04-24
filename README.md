# Argus

Multi-agent AI platform that automates code review at the pull-request level.

## Overview

Argus deploys specialized LLM agents in parallel to analyze pull requests across multiple dimensions:

- **Security** - Vulnerability detection, secrets exposure
- **Quality** - Code style, best practices, maintainability
- **Performance** - Performance anti-patterns, algorithmic efficiency
- **Testing** - Test coverage, test quality
- **Docs** - Documentation completeness, docstring quality
- **Best Practices** - Language/framework specific patterns

Agents synthesize findings into actionable feedback and post results as PR comments.

## Architecture

```
┌─────────────────┐     ┌─────────────┐     ┌──────────────┐
│  GitHub/GitLab  │────▶│   Gateway   │────▶│    Queue     │
│    Webhooks    │     │  (FastAPI)  │     │   (Celery)   │
└─────────────────┘     └─────────────┘     └──────┬───────┘
                                                  │
                     ┌────────────────────────────┼────────────┐
                     │                            │            │
              ┌──────▼──────┐            ┌───────▼────┐  ┌───▼────┐
              │   Gateway   │            │  Context   │  │Shared  │
              │   (Web)     │            │  Package   │  │Package │
              └─────────────┘            └────────────┘  └────────┘
                                                  │
                                    ┌─────────────┴─────────────┐
                                    │          Agents            │
                                    │    (LangGraph Orch.)      │
                                    └───────────────────────────┘
```

## Packages

- **shared** - Pydantic models, SQLAlchemy DB session, Celery queue primitives
- **context** - Vector embeddings (Qdrant), dependency graph (Neo4j), AST parsing
- **integrations** - GitHub App, GitLab MR clients, Slack/Notion adapters

## Apps

- **gateway** - FastAPI API gateway, webhook handling, auth, rate limiting
- **agents** - LangGraph orchestrator, specialized agents, fix suggestion engine
- **cli** - Typer CLI for local pre-commit review
- **web** - Web dashboard 