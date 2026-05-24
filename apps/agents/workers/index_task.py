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
    if redis_client is None:
        logger.error("index_repo_task called before worker connections were initialized")
        return

    raw = redis_client.get(f"index:latest:{repo_id}")
    latest_ref = str(raw) if raw is not None else ref

    try:
        files = get_repo_files(repo_full_name, installation_id, latest_ref)
        asyncio.run(_index_all(repo_id, files))
    except Exception:
        logger.exception("index_repo_task failed")


async def _index_all(repo_id: str, files: list[dict]) -> None:
    all_chunks = []
    for file in files:
        path: str = file["filename"]
        content: str = file["content"]
        language = extension_to_language(path)
        if not language:
            continue
        chunks = chunk_file(content, language=language, filepath=path)
        all_chunks.extend(chunks)

    try:
        await embed_chunks(repo_id, all_chunks)
    except Exception:
        logger.warning("embed_chunks failed during repo index", exc_info=True)
