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
from ai_parenting.backend.deps import (
    get_channel_router,
    get_orchestrator,
    get_push_engine,
    get_push_provider,
    get_skill_registry,
)
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
def skill_registry():
    """创建带有自动发现的 SkillRegistry。"""
    from pathlib import Path

    from ai_parenting.skills.registry import SkillRegistry

    registry = SkillRegistry()
    adapters_path = Path(__file__).resolve().parent.parent / "src" / "ai_parenting" / "skills" / "adapters"
    registry.discover_and_register(adapters_path)
    return registry


@pytest.fixture
def orchestrator(skill_registry) -> Orchestrator:
    """创建使用 MockProvider + SkillRegistry 的 Orchestrator。"""
    provider = MockProvider()
    return Orchestrator(provider=provider, skill_registry=skill_registry)


@pytest.fixture
def push_provider() -> MockPushProvider:
    """创建测试用 MockPushProvider。"""
    return MockPushProvider()


@pytest_asyncio.fixture
async def client(
    db_session: AsyncSession,
    orchestrator: Orchestrator,
    push_provider: MockPushProvider,
    skill_registry,
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

    def _override_get_skill_registry():
        return skill_registry

    # Mock ChannelRouter（避免测试时初始化真实渠道适配器）
    class _MockChannelRouter:
        async def send(self, user_id, channel, message):
            return {"status": "mock_sent"}

        async def health_check(self):
            return {"status": "healthy"}

    # Mock SmartPushEngine
    class _MockPushEngine:
        async def evaluate_rules(self, *args, **kwargs):
            return []

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_orchestrator] = _override_get_orchestrator
    app.dependency_overrides[get_push_provider] = _override_get_push_provider
    app.dependency_overrides[get_skill_registry] = _override_get_skill_registry
    app.dependency_overrides[get_channel_router] = lambda: _MockChannelRouter()
    app.dependency_overrides[get_push_engine] = lambda: _MockPushEngine()

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as ac:
        yield ac


@pytest.fixture
def default_user_id() -> uuid.UUID:
    """默认测试用户 ID。"""
    return uuid.UUID("00000000-0000-0000-0000-000000000001")
