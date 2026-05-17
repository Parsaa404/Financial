"""Test configuration — async fixtures for pytest."""
import asyncio
import uuid
from datetime import datetime, timezone
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import get_settings
from app.dependencies import get_db, get_current_user_id
from app.main import app
from app.models.base import Base
from app.services.auth_service import AuthService

# Use a test database
TEST_DATABASE_URL = get_settings().database_url.replace("/financeapp", "/financeapp_test")

test_engine = create_async_engine(TEST_DATABASE_URL, echo=False)
test_session_factory = async_sessionmaker(test_engine, expire_on_commit=False)


@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for the test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Create tables and provide a test DB session."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with test_session_factory() as session:
        yield session

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture(scope="function")
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """HTTP test client with overridden dependencies."""

    async def _get_test_db():
        yield db_session

    app.dependency_overrides[get_db] = _get_test_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession) -> dict:
    """Create a test user and return user data with tokens."""
    from app.models.user import User
    from app.repositories.user_repo import UserRepository

    repo = UserRepository(db_session)
    password = "TestPassword123!"
    user = await repo.create_user(
        email="test@example.com",
        password_hash=AuthService.hash_password(password),
    )

    access_token, expires_in = AuthService.create_access_token(user.id)

    return {
        "user": user,
        "id": user.id,
        "email": user.email,
        "password": password,
        "access_token": access_token,
    }


@pytest_asyncio.fixture
async def auth_headers(test_user: dict) -> dict:
    """Return Authorization headers for authenticated requests."""
    return {"Authorization": f"Bearer {test_user['access_token']}"}


@pytest_asyncio.fixture
async def test_account(db_session: AsyncSession, test_user: dict):
    """Create a test account."""
    from app.repositories.account_repo import AccountRepository

    repo = AccountRepository(db_session)
    return await repo.create_account(
        user_id=test_user["id"],
        name="Test Checking",
        account_type="checking",
        currency="USD",
        balance_cents=500000,  # $5,000.00
        is_primary=True,
    )
