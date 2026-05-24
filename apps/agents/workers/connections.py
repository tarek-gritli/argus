from __future__ import annotations

import asyncio
import threading
from contextlib import suppress

import redis as redis_lib
from shared.config import get_settings
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

redis_client: redis_lib.Redis | None = None

_loop: asyncio.AbstractEventLoop | None = None
_loop_thread: threading.Thread | None = None
_engine = None
session_factory: async_sessionmaker | None = None
_ready = threading.Event()
_closing = threading.Event()


def _loop_worker() -> None:
    global _loop
    _loop = asyncio.new_event_loop()
    asyncio.set_event_loop(_loop)
    _ready.set()
    _loop.run_forever()
    pending = asyncio.all_tasks(_loop)
    for task in pending:
        task.cancel()
    with suppress(Exception):
        _loop.run_until_complete(_loop.shutdown_asyncgens())
    _loop.close()


async def _async_init(database_url: str) -> None:
    global _engine, session_factory
    _engine = create_async_engine(
        database_url,
        pool_pre_ping=True,
        pool_size=3,
        max_overflow=2,
        pool_recycle=1800,
    )
    session_factory = async_sessionmaker(_engine, class_=AsyncSession, expire_on_commit=False)


def run_async(coro, timeout: float | None = 30.0):
    if _loop is None:
        raise RuntimeError("Async runtime not initialized")
    if _closing.is_set():
        raise RuntimeError("Async runtime is shutting down")
    return asyncio.run_coroutine_threadsafe(coro, _loop).result(timeout=timeout)


def get_session_factory() -> async_sessionmaker:
    if session_factory is None:
        raise RuntimeError("DB runtime not initialized")
    return session_factory


def init_connections() -> None:
    global _loop_thread, redis_client
    settings = get_settings()
    _closing.clear()

    redis_client = redis_lib.Redis.from_url(settings.redis_url, decode_responses=True)

    _loop_thread = threading.Thread(target=_loop_worker, daemon=True, name="argus-db-loop")
    _loop_thread.start()
    _ready.wait()
    run_async(_async_init(settings.database_url))


def close_connections() -> None:
    global redis_client, _engine, session_factory

    _closing.set()

    if redis_client is not None:
        redis_client.close()
        redis_client = None

    if _engine is not None and _loop is not None:
        with suppress(Exception):
            run_async(_engine.dispose(), timeout=30.0)
        _engine = None
        session_factory = None

    if _loop is not None:
        _loop.call_soon_threadsafe(_loop.stop)
    if _loop_thread is not None:
        _loop_thread.join(timeout=10)
