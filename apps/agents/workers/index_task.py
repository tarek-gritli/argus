from __future__ import annotations

import asyncio
import logging

from context.chunker import chunk_file, extension_to_language
from context.embeddings import embed_chunks
from integrations.github.pr import get_repo_files
from workers.connections import redis_client

logger = logging.getLogger(__name__)


def index_repo_task(repo_id: str, installation_id: int, repo_full_name: str, ref: str = "main") -> None:
    """Celery-callable. Reads the latest ref from Redis (set by the gateway at schedule time)
    and indexes that commit. The gateway debounces scheduling so this task fires at most
    once per 5-minute window, always for the most recent push in that window.
    """
    logger.info("index_repo_task starting: repo=%s repo_id=%s", repo_full_name, repo_id)

    try:
        raw = redis_client.get(f"index:latest:{repo_id}") if redis_client is not None else None
        latest_ref = str(raw) if raw is not None else ref
    except Exception:
        logger.warning("Redis unavailable, falling back to ref=%s for repo=%s", ref, repo_full_name, exc_info=True)
        latest_ref = ref

    logger.info("index_repo_task: fetching files at ref=%s for repo=%s", latest_ref, repo_full_name)
    try:
        files = get_repo_files(repo_full_name, installation_id, latest_ref)
        logger.info("index_repo_task: fetched %d files from %s", len(files), repo_full_name)
        asyncio.run(_index_all(repo_id, files))
        logger.info("index_repo_task: completed successfully for repo=%s", repo_full_name)
    except Exception:
        logger.exception("index_repo_task failed for repo=%s", repo_full_name)


async def _index_all(repo_id: str, files: list[dict]) -> None:
    all_chunks = []
    skipped = 0
    for file in files:
        path: str = file["filename"]
        content: str = file["content"]
        language = extension_to_language(path)
        if not language:
            skipped += 1
            continue
        chunks = chunk_file(content, language=language, filepath=path)
        all_chunks.extend(chunks)

    logger.info(
        "_index_all: %d files → %d chunks (%d skipped — unsupported language)",
        len(files),
        len(all_chunks),
        skipped,
    )

    if not all_chunks:
        logger.warning("_index_all: no chunks to embed for repo_id=%s — nothing indexed", repo_id)
        return

    try:
        await embed_chunks(repo_id, all_chunks)
        logger.info("_index_all: embed_chunks done for repo_id=%s", repo_id)
    except Exception:
        logger.warning("embed_chunks failed during repo index for repo_id=%s", repo_id, exc_info=True)
