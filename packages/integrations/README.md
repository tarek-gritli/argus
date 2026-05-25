# Argus Integrations

External API clients. No business logic — pure I/O adapters.

## Active

- **github/client.py** — `get_installation_client(installation_id)` → PyGithub client; installation tokens cached in-memory with TTL (3600s, refreshed 60s before expiry)
- **github/pr.py** — `get_pr()`, `get_pr_diff()`, `get_pr_files()`, `get_pr_file_content()`, `post_issue_comment()`, `post_findings_as_review()`, `update_pr_body()`
- **github/webhook.py** — `validate_signature(payload, signature, secret)` → bool

## Stubs

- **gitlab/** — Phase 2, not implemented

## GitHub App Rules

- Private key loaded from `GITHUB_PRIVATE_KEY_B64` env var (base64) via `get_settings()` — never read from `.pem` at request time
- Use `Auth.AppAuth` + `GithubIntegration(auth=…)` — never the deprecated `integration_id=` style