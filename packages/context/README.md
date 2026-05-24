# Argus Context

Semantic context retrieval for code review agents. Indexes repo code into Qdrant and surfaces relevant chunks at review time.

## Components

- **chunker** — AST-based code splitting (function/class level) via tree-sitter; 10 languages supported; Dart falls back to line-window
- **embeddings** — Voyage AI (`voyage-code-3`, 1024-dim) → Qdrant; blue-green collection swap for zero-downtime reindex
- **cache** — Redis TTL cache (1h) for embedding lookups to avoid re-embedding identical chunks
- **bundle** — `ContextBundle` passed read-only to each agent at review time
- **history** — rejected finding suppression; loads per-org/repo rejected keys from DB

## Indexing

Triggered by a separate Celery task (`index_repo`) on push — not on PR open. Context is best-effort: if Qdrant is unavailable, review proceeds with an empty bundle.

## Supported Languages

Python, JavaScript, TypeScript, Go, Java, Kotlin, C++, C#, Ruby, PHP. Dart uses line-window fallback.

## Environment

```bash
QDRANT_URL=http://localhost:6333
QDRANT_API_KEY=          # empty for local dev
VOYAGE_API_KEY=
```