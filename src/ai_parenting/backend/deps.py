"""FastAPI 依赖注入。

提供 Orchestrator、PushProvider 等共享依赖的工厂。
"""

from __future__ import annotations

from functools import lru_cache

from ai_parenting.backend.config import settings
from ai_parenting.backend.services.push_service import MockPushProvider, PushProvider
from ai_parenting.orchestrator import Orchestrator
from ai_parenting.providers.mock_provider import MockProvider


@lru_cache(maxsize=1)
def _create_orchestrator() -> Orchestrator:
    """创建 Orchestrator 单例（使用 MockProvider）。"""
    provider = MockProvider()
    return Orchestrator(provider=provider)


def get_orchestrator() -> Orchestrator:
    """FastAPI 依赖：获取 Orchestrator 实例。"""
    return _create_orchestrator()


@lru_cache(maxsize=1)
def _create_push_provider() -> PushProvider:
    """创建 PushProvider 单例（当前使用 MockPushProvider）。"""
    return MockPushProvider()


def get_push_provider() -> PushProvider:
    """FastAPI 依赖：获取 PushProvider 实例。"""
    return _create_push_provider()
