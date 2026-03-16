"""后端测试配置和 fixtures。

使用 SQLite + aiosqlite 作为测试数据库，
不依赖 PostgreSQL 实例。
"""

from __future__ import annotations

import asyncio
import uuid
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from ai_parenting.backend.database import get_db
from ai_parenting.backend.deps import get_orchestrator, get_push_provider
from ai_parenting.backend.models import Base
from ai_parenting.backend.services.push_service import MockPushProvider, PushProvider
from ai_parenting.orchestrator import Orchestrator
from ai_parenting.providers.mock_provider import MockProvider


# ---------------------------------------------------------------------------
# SQLite 测试引擎（替代 PostgreSQL）
# ---------------------------------------------------------------------------

# 使用 SQLite 内存数据库进行测试
_TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

_test_engine = create_async_engine(_TEST_DATABASE_URL, echo=False)

_test_session_factory = async_sessionmaker(
    _test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """创建测试数据库会话（每个测试自动建表/销表）。"""
    # 由于 SQLite 不支持 PostgreSQL 特有类型，需做适配
    async with _test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with _test_session_factory() as session:
        yield session

    async with _test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
def orchestrator() -> Orchestrator:
    """创建使用 MockProvider 的 Orchestrator。"""
    provider = MockProvider()
    return Orchestrator(provider=provider)


@pytest.fixture
def push_provider() -> MockPushProvider:
    """创建测试用 MockPushProvider。"""
    return MockPushProvider()


@pytest_asyncio.fixture
async def client(
    db_session: AsyncSession,
    orchestrator: Orchestrator,
    push_provider: MockPushProvider,
) -> AsyncGenerator[AsyncClient, None]:
    """创建测试用 HTTP 客户端。"""
    from ai_parenting.backend.app import create_app

    app = create_app()

    # 覆盖依赖
    async def _override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    def _override_get_orchestrator() -> Orchestrator:
        return orchestrator

    def _override_get_push_provider() -> PushProvider:
        return push_provider

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_orchestrator] = _override_get_orchestrator
    app.dependency_overrides[get_push_provider] = _override_get_push_provider

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as ac:
        yield ac


@pytest.fixture
def default_user_id() -> uuid.UUID:
    """默认测试用户 ID。"""
    return uuid.UUID("00000000-0000-0000-0000-000000000001")
