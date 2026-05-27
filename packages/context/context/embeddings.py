from __future__ import annotations

import hashlib
import logging
import uuid
from functools import lru_cache

from shared.config import get_settings

from .cache import cache_get, cache_set
from .chunker import CodeChunk

logger = logging.getLogger(__name__)

_COLLECTION_PREFIX = "repo_"
_EMBED_MODEL = "voyage-code-3"
_EMBED_DIM = 1024


@lru_cache(maxsize=1)
def _get_voyage():
    from voyageai.client_async import AsyncClient

    return AsyncClient(api_key=get_settings().voyage_api_key)


@lru_cache(maxsize=1)
def _get_qdrant():
    from qdrant_client import AsyncQdrantClient

    s = get_settings()
    return AsyncQdrantClient(url=s.qdrant_url, api_key=s.qdrant_api_key or None)


def _collection(repo_id: str) -> str:
    return f"{_COLLECTION_PREFIX}{repo_id}"


def _cache_key(content: str) -> str:
    return f"emb:{hashlib.sha256(content.encode()).hexdigest()}"


async def _prepare_tmp_collection(repo_id: str) -> str:
    """Create a uniquely-named tmp collection. Returns tmp_name for callers to upsert into.

    Uses a UUID suffix so the live alias keeps serving the previous collection uninterrupted
    while the new one is being built. Orphaned __tmp_* collections from prior crashed runs
    are left in place — cleaning them up here risks racing with another in-flight indexer.
    """
    from qdrant_client.models import Distance, VectorParams

    qdrant = _get_qdrant()
    tmp_name = f"{_collection(repo_id)}__tmp_{uuid.uuid4().hex[:8]}"
    await qdrant.create_collection(
        tmp_name,
        vectors_config=VectorParams(size=_EMBED_DIM, distance=Distance.COSINE),
    )
    return tmp_name


async def _promote_tmp_collection(repo_id: str, tmp_name: str) -> None:
    """Atomically swap the live alias to point at tmp_name, then delete the old real collection."""
    from qdrant_client.models import CreateAlias, CreateAliasOperation

    qdrant = _get_qdrant()
    alias_name = _collection(repo_id)

    existing_aliases = {a.alias_name: a.collection_name for a in (await qdrant.get_aliases()).aliases}
    old_collection = existing_aliases.get(alias_name)

    # Single CreateAliasOperation is atomic and overwrites any existing alias with the same name.
    await qdrant.update_collection_aliases(change_aliases_operations=[CreateAliasOperation(create_alias=CreateAlias(collection_name=tmp_name, alias_name=alias_name))])

    if old_collection and old_collection != tmp_name:
        try:
            await qdrant.delete_collection(old_collection)
        except Exception:
            logger.warning("Failed to delete old collection %s — it may have already been removed", old_collection)


async def embed_chunks(repo_id: str, chunks: list[CodeChunk]) -> None:
    """Embed chunks and upsert into Qdrant. Redis-cached per content hash. Non-fatal on outage."""
    if not chunks:
        return
    tmp_name: str | None = None
    try:
        voyage = _get_voyage()
        qdrant = _get_qdrant()
        tmp_name = await _prepare_tmp_collection(repo_id)

        vectors: list[list[float]] = []
        uncached_indices: list[int] = []
        uncached_contents: list[str] = []

        for i, chunk in enumerate(chunks):
            key = _cache_key(chunk.content)
            cached = await cache_get(key)
            if cached is not None:
                vectors.append(cached)
            else:
                vectors.append([])  # placeholder
                uncached_indices.append(i)
                uncached_contents.append(chunk.content)

        if uncached_contents:
            result = await voyage.embed(uncached_contents, model=_EMBED_MODEL, input_type="document")
            for chunk_idx, vec in zip(uncached_indices, result.embeddings):
                vec = [float(v) for v in vec]
                vectors[chunk_idx] = vec
                key = _cache_key(chunks[chunk_idx].content)
                await cache_set(key, vec)

        from qdrant_client.models import PointStruct

        points = [
            PointStruct(
                id=str(uuid.UUID(hashlib.sha256(f"{repo_id}:{c.filepath}:{c.start_line}".encode()).hexdigest()[:32])),
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
        await qdrant.upsert(collection_name=tmp_name, points=points)
        await _promote_tmp_collection(repo_id, tmp_name)
    except Exception:
        if tmp_name:
            try:
                await _get_qdrant().delete_collection(tmp_name)
            except Exception:
                pass
        logger.warning("embed_chunks failed — indexing skipped", exc_info=True)


async def search_similar(repo_id: str, query: str, top_k: int = 5) -> list[dict]:
    """Search Qdrant for chunks semantically similar to query. Returns [] on outage."""
    try:
        voyage = _get_voyage()
        qdrant = _get_qdrant()
        result = await voyage.embed([query], model=_EMBED_MODEL, input_type="query")
        vec = result.embeddings[0]
        response = await qdrant.query_points(
            collection_name=_collection(repo_id),
            query=[float(v) for v in vec],
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
            for h in response.points
            if h.payload
        ]
    except Exception:
        logger.warning("search_similar failed — returning empty context", exc_info=True)
        return []
