# uv Commands Guide

This project uses [uv](https://docs.astral.sh/uv/) as a workspace with multiple apps and packages.

## Project Structure

```
argus/
├── pyproject.toml          # Workspace root (shared config + dev deps)
├── apps/
│   ├── gateway/            # FastAPI API gateway
│   ├── agents/             # LangGraph orchestrator
│   └── cli/                # Typer CLI
└── packages/
    ├── shared/             # Shared models & utilities
    ├── context/            # Vector embeddings & AST parsing
    └── integrations/       # GitHub, GitLab, Slack, Notion clients
```

All members are part of a single workspace managed from the root `pyproject.toml`.

---

## Essential Commands

### Sync the Environment

Installs all workspace members and their dependencies into `.venv/`.

```bash
uv sync
```

Always run this after pulling changes or modifying dependencies.

### Add an External Dependency

Add a PyPI package to a specific workspace member:

```bash
# From the workspace root, target a specific member:
uv add --package argus-gateway fastapi uvicorn
uv add --package argus-agents langgraph
uv add --package argus-cli typer
```

### Add an Internal Dependency (Workspace Package)

Make one workspace member depend on another. The workspace automatically handles `tool.uv.sources`:

```bash
# Example: gateway imports from integrations (github, gitlab)
uv add --package argus-gateway argus-integrations

# Example: gateway imports from shared (db, queue, models, schemas)
uv add --package argus-gateway argus-shared

# Example: agents depends on shared and context
uv add --package argus-agents argus-shared
uv add --package argus-agents argus-context

# Example: CLI imports from shared and integrations
uv add --package argus-cli argus-shared
uv add --package argus-cli argus-integrations
```

uv automatically resolves internal packages via `tool.uv.sources` with `workspace = true`.

### Remove a Dependency

```bash
uv remove --package argus-gateway some-package
```

### Run a Specific App

```bash
# Run the gateway entry point
uv run --package argus-gateway gateway

# Run the CLI entry point
uv run --package argus-cli argus-cli

# Run the agents entry point
uv run --package argus-agents argus-agents
```

Or run a Python module directly:

```bash
uv run --package argus-gateway python -m gateway.main
```

### Run Arbitrary Commands in the Environment

```bash
# Run ruff
uv run ruff check .

# Run a one-off script
uv run python scripts/example.py

# Open a Python shell with all workspace packages available
uv run python
```

### Update Dependencies

```bash
# Re-resolve and update all dependencies to latest compatible versions
uv lock --upgrade

# Update a specific package
uv lock --upgrade-package fastapi
```

### Show Resolved Dependencies

```bash
uv tree
```

### Clean the Environment

```bash
# Remove .venv/ and start fresh
rm -rf .venv
uv sync
```

---

## Quick Reference

| Task | Command |
|------|---------|
| Install everything | `uv sync` |
| Add external dep to an app | `uv add --package argus-gateway <pkg>` |
| Add internal dep | `uv add --package argus-gateway argus-shared` |
| Remove a dep | `uv remove --package argus-gateway <pkg>` |
| Run an app | `uv run --package argus-gateway gateway` |
| Update all deps | `uv lock --upgrade` |
| View dep tree | `uv tree` |
