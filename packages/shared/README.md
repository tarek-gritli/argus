# Argus Shared

Shared Pydantic models, SQLAlchemy DB session, and Celery queue primitives.

## Contents

- **Models** - Pydantic schemas for review requests, findings, comments
- **Database** - SQLAlchemy session factory, base models, migrations
- **Queue** - Celery task definitions, serializers, queue configuration

## Usage

```python
from shared import ReviewRequest, Finding, get_session

request = ReviewRequest(...)
async with get_session() as session:
    ...
```