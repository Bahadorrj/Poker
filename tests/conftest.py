import os

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test.db")
os.environ.setdefault("JWT_SECRET", "test-secret")
os.environ.setdefault("JWT_LIFETIME_HOURS", "1")
os.environ.setdefault("RESET_PASSWORD_SECRET", "test-secret")
os.environ.setdefault("RESET_PASSWORD_TOKEN_LIFETIME_HOURS", "1")
os.environ.setdefault("VERIFICATION_SECRET", "test-secret")
os.environ.setdefault("VERIFICATION_TOKEN_LIFETIME_HOURS", "1")

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.models import Base

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture(scope="session")
async def engine():
    engine = create_async_engine(TEST_DATABASE_URL)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    # Teardown
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture()
async def db_session(engine):
    async with async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )() as session:
        yield session
        await session.rollback()  # Undo changes after each test
