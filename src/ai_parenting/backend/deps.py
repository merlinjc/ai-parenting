"""FastAPI 依赖注入。

提供 Orchestrator、PushProvider 等共享依赖的工厂。
"""

from __future__ import annotations

from functools import lru_cache

from ai_parenting.backend.config import settings
from ai_parenting.backend.services.push_service import MockPushProvider, PushProvider
from ai_parenting.orchestrator import Orchestrator
from ai_parenting.providers.base import ModelProvider
from ai_parenting.providers.mock_provider import MockProvider


def _create_provider() -> ModelProvider:
    """根据配置创建对应的 AI 模型供应商。"""
    if settings.ai_provider == "hunyuan":
        from ai_parenting.providers.hunyuan_provider import HunyuanProvider

        return HunyuanProvider(
            api_key=settings.hunyuan_api_key,
            base_url=settings.hunyuan_base_url,
            model=settings.hunyuan_model,
        )
    # 默认使用 MockProvider
    return MockProvider()


@lru_cache(maxsize=1)
def _create_orchestrator() -> Orchestrator:
    """创建 Orchestrator 单例（根据配置选择 AI Provider）。"""
    provider = _create_provider()
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
