from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from context.chunker import CodeChunk
from context.embeddings import embed_chunks, search_similar


def _make_chunk(
    content: str = "def foo(): pass",
    filepath: str = "a.py",
    start: int = 1,
    end: int = 1,
) -> CodeChunk:
    return CodeChunk(
        filepath=filepath,
        start_line=start,
        end_line=end,
        content=content,
        token_count=10,
        function_name="foo",
    )


@pytest.mark.asyncio
async def test_embed_chunks_calls_voyage_and_upserts():
    chunk = _make_chunk()
    mock_voyage = MagicMock()
    mock_voyage.embed = AsyncMock(return_value=MagicMock(embeddings=[[0.1] * 1024]))
    mock_qdrant = AsyncMock()
    mock_qdrant.get_collections = AsyncMock(return_value=MagicMock(collections=[]))

    with (
        patch("context.embeddings._get_voyage", return_value=mock_voyage),
        patch("context.embeddings._get_qdrant", return_value=mock_qdrant),
        patch("context.embeddings.cache_get", new=AsyncMock(return_value=None)),
        patch("context.embeddings.cache_set", new=AsyncMock()),
    ):
        await embed_chunks("repo_abc", [chunk])

    mock_qdrant.upsert.assert_called_once()


@pytest.mark.asyncio
async def test_embed_chunks_uses_redis_cache():
    chunk = _make_chunk()
    cached_vec = [0.2] * 1024
    mock_qdrant = AsyncMock()
    mock_qdrant.get_collections = AsyncMock(return_value=MagicMock(collections=[]))
    mock_voyage = MagicMock()

    with (
        patch("context.embeddings._get_voyage", return_value=mock_voyage),
        patch("context.embeddings._get_qdrant", return_value=mock_qdrant),
        patch("context.embeddings.cache_get", new=AsyncMock(return_value=cached_vec)),
        patch("context.embeddings.cache_set", new=AsyncMock()),
    ):
        await embed_chunks("repo_abc", [chunk])

    mock_voyage.embed.assert_not_called()
    mock_qdrant.upsert.assert_called_once()


@pytest.mark.asyncio
async def test_search_similar_returns_chunks():
    mock_voyage = MagicMock()
    mock_voyage.embed = AsyncMock(return_value=MagicMock(embeddings=[[0.1] * 1024]))
    mock_qdrant = AsyncMock()
    mock_point = MagicMock(
        payload={
            "filepath": "a.py",
            "start_line": 1,
            "end_line": 5,
            "content": "def foo(): pass",
            "function_name": "foo",
            "class_name": None,
        },
        score=0.9,
    )
    mock_qdrant.query_points.return_value = MagicMock(points=[mock_point])

    with (
        patch("context.embeddings._get_voyage", return_value=mock_voyage),
        patch("context.embeddings._get_qdrant", return_value=mock_qdrant),
    ):
        results = await search_similar("repo_abc", "find authentication logic", top_k=3)

    assert len(results) == 1
    assert results[0]["filepath"] == "a.py"
    assert results[0]["score"] == 0.9
    assert results[0]["function_name"] == "foo"


@pytest.mark.asyncio
async def test_embed_chunks_graceful_on_qdrant_outage():
    chunk = _make_chunk()
    mock_voyage = MagicMock()
    mock_voyage.embed = AsyncMock(return_value=MagicMock(embeddings=[[0.1] * 1024]))
    mock_qdrant = AsyncMock()
    mock_qdrant.get_collections = AsyncMock(return_value=MagicMock(collections=[]))
    mock_qdrant.upsert.side_effect = Exception("connection refused")

    with (
        patch("context.embeddings._get_voyage", return_value=mock_voyage),
        patch("context.embeddings._get_qdrant", return_value=mock_qdrant),
        patch("context.embeddings.cache_get", new=AsyncMock(return_value=None)),
        patch("context.embeddings.cache_set", new=AsyncMock()),
    ):
        # Must not raise — indexing failure is non-fatal
        await embed_chunks("repo_abc", [chunk])


@pytest.mark.asyncio
async def test_search_similar_returns_empty_on_outage():
    mock_voyage = MagicMock()
    mock_voyage.embed = AsyncMock(side_effect=Exception("Voyage down"))
    mock_qdrant = AsyncMock()

    with (
        patch("context.embeddings._get_voyage", return_value=mock_voyage),
        patch("context.embeddings._get_qdrant", return_value=mock_qdrant),
    ):
        results = await search_similar("repo_abc", "find auth", top_k=3)

    assert results == []
    mock_qdrant.query_points.assert_not_called()
