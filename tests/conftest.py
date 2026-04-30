import datetime
import os
import uuid

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Test environment variables
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"
os.environ.setdefault("DATABASE_URL", TEST_DATABASE_URL)
os.environ.setdefault("JWT_SECRET", "test-secret")
os.environ.setdefault("JWT_LIFETIME_HOURS", "1")
os.environ.setdefault("RESET_PASSWORD_SECRET", "test-secret")
os.environ.setdefault("RESET_PASSWORD_TOKEN_LIFETIME_HOURS", "1")
os.environ.setdefault("VERIFICATION_SECRET", "test-secret")
os.environ.setdefault("VERIFICATION_TOKEN_LIFETIME_HOURS", "1")


from app.db import get_async_session
from app.main import app
from app.models import Base, User
from app.routers.auth import current_active_user


@pytest_asyncio.fixture(scope="function")
async def engine():
    engine = create_async_engine(TEST_DATABASE_URL)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    # Teardown
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture(scope="function")
async def db_session(engine):
    async with async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )() as session:
        yield session
        await session.rollback()  # Undo changes after each test


def make_user(is_superuser: bool = False) -> User:
    user = User()
    user.id = uuid.uuid4()
    user.username = "testuser"
    user.created_at = datetime.datetime.now()
    user.email = "test@example.com"
    user.hashed_password = "testhash"
    user.is_active = True
    user.is_superuser = is_superuser
    user.is_verified = True
    return user


@pytest_asyncio.fixture
async def test_user(db_session) -> User:
    user = make_user()
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def superuser(db_session) -> User:
    user = make_user(is_superuser=True)
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def client(db_session, test_user):
    def override_get_session():
        yield db_session

    def override_current_user():
        return test_user

    app.dependency_overrides[get_async_session] = override_get_session
    app.dependency_overrides[current_active_user] = override_current_user

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def superuser_client(db_session, superuser):
    def override_get_session():
        yield db_session

    def override_current_user():
        return superuser

    app.dependency_overrides[get_async_session] = override_get_session
    app.dependency_overrides[current_active_user] = override_current_user

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac

    app.dependency_overrides.clear()
