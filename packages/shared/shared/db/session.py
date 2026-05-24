from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from shared.config import get_settings

_engine = None
_session_factory = None


def _get_engine():
    global _engine
    if _engine is None:
        settings = get_settings()
        _engine = create_async_engine(settings.database_url, echo=False)
    return _engine


def _get_session_factory():
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(_get_engine(), expire_on_commit=False)
    return _session_factory


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with _get_session_factory()() as session:
        yield session


@asynccontextmanager
async def session_context() -> AsyncGenerator[AsyncSession, None]:
    async with _get_session_factory()() as session:
        yield session


@asynccontextmanager
async def fresh_session_context() -> AsyncGenerator[AsyncSession, None]:
    """Create a throw-away engine+session bound to the current event loop.

    Use this inside asyncio.run() calls (e.g. Celery tasks) where the module-level
    engine may have been created on a different loop, which causes asyncpg to raise
    'Future attached to a different loop'.
    """
    settings = get_settings()
    engine = create_async_engine(settings.database_url, echo=False)
    try:
        factory = async_sessionmaker(engine, expire_on_commit=False)
        async with factory() as session:
            yield session
    finally:
        await engine.dispose()
