# Argus Shared

Cross-app models, schemas, DB session, and queue signatures. Single source of truth for data contracts.

## Contents

- **models/** — SQLAlchemy ORM: `Org`, `User`, `UserOrg`, `OrgBilling`, `Repo`, `Review`, `Finding`, `ApiKey`
- **schemas/** — Pydantic: `FindingSchema` (canonical agent output), `FixSchema`, `ReviewSchema`
- **db/** — async SQLAlchemy engine + session factory (`get_session`, `fresh_session_context`)
- **config.py** — `Settings` (pydantic-settings, loaded via `get_settings()` with `lru_cache`)
- **queue/tasks.py** — Celery task signatures only (not the worker)

## Key Schema

```python
class FindingSchema(BaseModel):
    agent: Literal["security", "quality", "testing", "documentation", "ticket_compliance"]
    severity: Literal["critical", "high", "medium", "low", "info"]
    file: str           # repo-relative path
    line_start: int
    line_end: int
    title: str
    description: str
    suggestion: str | None
    confidence: float   # 0.0–1.0
    fix: FixSchema | None
```

## Rules

- No app-specific logic
- No HTTP code
- No LLM calls
- If only one app uses it, it does not belong here