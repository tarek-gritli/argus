from __future__ import annotations

import hashlib
import json
import logging
from functools import lru_cache

from shared.config import get_settings

from .chunker import CodeChunk

logger = logging.getLogger(__name__)

_COLLECTION_PREFIX = "repo_"
_EMBED_MODEL = "voyage-code-3"
_EMBED_DIM = 1024
_CACHE_TTL = 3600


@lru_cache(maxsize=1)
def _get_voyage():
    import voyageai

    return voyageai.Client(api_key=get_settings().voyage_api_key)


@lru_cache(maxsize=1)
def _get_qdrant():
    from qdrant_client import AsyncQdrantClient

    s = get_settings()
    return AsyncQdrantClient(url=s.qdrant_url, api_key=s.qdrant_api_key or None)


def _get_redis():
    from shared.db import get_redis_client

    return get_redis_client()


def _collection(repo_id: str) -> str:
    return f"{_COLLECTION_PREFIX}{repo_id}"


def _cache_key(content: str) -> str:
    return f"emb:{hashlib.sha256(content.encode()).hexdigest()}"


async def ensure_collection(repo_id: str) -> None:
    from qdrant_client.models import Distance, VectorParams

    qdrant = _get_qdrant()
    name = _collection(repo_id)
    existing = [c.name for c in (await qdrant.get_collections()).collections]
    if name not in existing:
        await qdrant.create_collection(
            name,
            vectors_config=VectorParams(size=_EMBED_DIM, distance=Distance.COSINE),
        )


async def embed_chunks(repo_id: str, chunks: list[CodeChunk]) -> None:
    """Embed chunks and upsert into Qdrant. Redis-cached per content hash. Non-fatal on outage."""
    if not chunks:
        return
    try:
        redis = _get_redis()
        voyage = _get_voyage()
        qdrant = _get_qdrant()
        await ensure_collection(repo_id)

        vectors: list[list[float]] = []
        uncached_indices: list[int] = []
        uncached_contents: list[str] = []

        for i, chunk in enumerate(chunks):
            key = _cache_key(chunk.content)
            cached = await redis.get(key)
            if cached:
                vectors.append(json.loads(cached))
            else:
                vectors.append([])  # placeholder
                uncached_indices.append(i)
                uncached_contents.append(chunk.content)

        if uncached_contents:
            result = voyage.embed(uncached_contents, model=_EMBED_MODEL, input_type="document")
            for chunk_idx, vec in zip(uncached_indices, result.embeddings):
                vectors[chunk_idx] = vec
                key = _cache_key(chunks[chunk_idx].content)
                await redis.setex(key, _CACHE_TTL, json.dumps(vec))

        from qdrant_client.models import PointStruct

        points = [
            PointStruct(
                id=hashlib.sha256(f"{repo_id}:{c.filepath}:{c.start_line}".encode()).hexdigest()[:16],
                vector=vec,
                payload={
                    "filepath": c.filepath,
                    "start_line": c.start_line,
                    "end_line": c.end_line,
                    "content": c.content,
                    "function_name": c.function_name,
                    "class_name": c.class_name,
                    "repo_id": repo_id,
                },
            )
            for c, vec in zip(chunks, vectors)
        ]
        await qdrant.upsert(collection_name=_collection(repo_id), points=points)
    except Exception:
        logger.warning("embed_chunks failed — indexing skipped", exc_info=True)


async def search_similar(repo_id: str, query: str, top_k: int = 5) -> list[dict]:
    """Search Qdrant for chunks semantically similar to query. Returns [] on outage."""
    try:
        voyage = _get_voyage()
        qdrant = _get_qdrant()
        result = voyage.embed([query], model=_EMBED_MODEL, input_type="query")
        vec = result.embeddings[0]
        hits = await qdrant.search(
            collection_name=_collection(repo_id),
            query_vector=vec,
            limit=top_k,
        )
        return [
            {
                "filepath": h.payload["filepath"],
                "start_line": h.payload["start_line"],
                "end_line": h.payload["end_line"],
                "content": h.payload["content"],
                "function_name": h.payload.get("function_name"),
                "class_name": h.payload.get("class_name"),
                "score": h.score,
            }
            for h in hits
        ]
    except Exception:
        logger.warning("search_similar failed — returning empty context", exc_info=True)
        return []
