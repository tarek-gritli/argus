# Argus CLI

Typer-based CLI for local pre-commit review and watch mode.

## Commands

### `argus review`

Run local code review on a directory or diff.

```bash
argus review --path ./src
argus review --diff HEAD~1
argus review --staged
```

### `argus apply`

Apply suggested fixes from review results.

```bash
argus apply --review-id <id>
argus apply --auto
```

### `argus watch`

Watch mode for continuous review on file changes.

```bash
argus watch --path ./src
argus watch --debounce 2s
```

### `argus status`

Check status of previous reviews.

```bash
argus status
argus status --review-id <id>
```