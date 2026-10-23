import pytest_asyncio
from shared.models import AuthIdentity, Base, Org, OrgBilling, OrgInvite, User, UserOrg
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

TABLES = [t.__table__ for t in (User, Org, UserOrg, OrgBilling, AuthIdentity, OrgInvite)]


@pytest_asyncio.fixture
async def session():
    engine = create_async_engine("sqlite+aiosqlite://", poolclass=StaticPool)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all, tables=TABLES)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as s:
        s.factory = factory
        yield s
    await engine.dispose()
