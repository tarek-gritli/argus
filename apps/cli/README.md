# Argus CLI

Typer-based CLI for local pre-commit code review.

## Commands

```bash
argus login       # Authenticate via browser (GitHub OAuth)
argus review      # Review uncommitted changes in the current repo
argus review src/auth.py src/db.py   # Scope review to specific files
```

## How It Works

### Login

Opens a browser to complete GitHub OAuth. On success, stores a JWT token at `~/.config/argus/credentials.json` (mode `0600`).

### Review

1. Runs `git diff HEAD` to collect local changes
2. POSTs the diff to `/api/v1/reviews/local` — gateway enqueues a Celery task
3. Streams findings via SSE as each agent completes; falls back to polling if SSE is unavailable
4. Prints findings live during streaming; shows a table on polling fallback

## Installation

```bash
curl -fsSL https://raw.githubusercontent.com/tarek-gritli/argus/<tag>/install.sh | sh
```

Binaries are distributed via GitHub Releases for Linux x86_64, macOS Intel, and macOS Apple Silicon. SHA-256 checksums are published alongside each release and verified automatically by `install.sh`.

## Structure

```
apps/cli/
├── main.py              # Typer app — registers login + review
├── auth.py              # Token load/save/clear (~/.config/argus/credentials.json)
├── client.py            # httpx.Client factory (Bearer token, 120s timeout)
├── commands/
│   ├── login.py         # Browser OAuth flow via CLI session API
│   └── review.py        # Local diff review — SSE streaming + polling fallback
└── argus.spec           # PyInstaller spec for binary builds
```

## Configuration

The CLI talks to the gateway at `http://localhost:8000` by default. Set `ARGUS_BASE_URL` to point at a remote instance.
