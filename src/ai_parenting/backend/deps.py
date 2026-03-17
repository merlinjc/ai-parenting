"""FastAPI 依赖注入。

提供 Orchestrator、SkillRegistry、PushProvider、ChannelRouter、SmartPushEngine 等共享依赖的工厂。

Phase 3 升级：
- 新增 SkillRegistry 单例创建 + 自动发现注册
- Orchestrator 注入 SkillRegistry（不再仅依赖直接导入渲染器）
"""

from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path

from ai_parenting.backend.config import settings
from ai_parenting.backend.services.push_service import MockPushProvider, PushProvider
from ai_parenting.orchestrator import Orchestrator
from ai_parenting.providers.base import ModelProvider
from ai_parenting.providers.mock_provider import MockProvider
from ai_parenting.skills.registry import SkillRegistry

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# SkillRegistry（Phase 3）
# ---------------------------------------------------------------------------

_skill_registry_instance: SkillRegistry | None = None


def _create_skill_registry() -> SkillRegistry:
    """创建 SkillRegistry 并自动发现注册内置适配器。"""
    registry = SkillRegistry()

    # 自动发现 ai_parenting.skills.adapters 下的所有 Skill 子类
    adapters_path = Path(__file__).resolve().parent.parent / "skills" / "adapters"
    discovered = registry.discover_and_register(adapters_path)
    logger.info(
        "SkillRegistry initialized: %d skills discovered from adapters/",
        discovered,
    )
    return registry


def get_skill_registry() -> SkillRegistry:
    """FastAPI 依赖：获取 SkillRegistry 单例（懒加载）。"""
    global _skill_registry_instance
    if _skill_registry_instance is None:
        _skill_registry_instance = _create_skill_registry()
    return _skill_registry_instance


# ---------------------------------------------------------------------------
# AI Provider / Orchestrator
# ---------------------------------------------------------------------------


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
    """创建 Orchestrator 单例。

    Phase 3: 注入 SkillRegistry，优先通过 Skill 接口路由。
    """
    provider = _create_provider()
    registry = get_skill_registry()
    orchestrator = Orchestrator(provider=provider, skill_registry=registry)
    logger.info(
        "Orchestrator initialized with SkillRegistry (%d skills: %s)",
        registry.skill_count,
        registry.skill_names,
    )
    return orchestrator


def get_orchestrator() -> Orchestrator:
    """FastAPI 依赖：获取 Orchestrator 实例。"""
    return _create_orchestrator()


# ---------------------------------------------------------------------------
# Push Provider（Legacy 兼容 — 桥接到 ChannelRouter）
# ---------------------------------------------------------------------------


class _ChannelRouterBridge(PushProvider):
    """将 ChannelRouter 桥接为 PushProvider 接口。

    供 Legacy scheduler_service 等仍使用 PushProvider 的模块过渡使用。
    """

    def __init__(self, channel_router: object) -> None:
        self._router = channel_router

    async def send_notification(self, notification: object) -> object:
        """通过 ChannelRouter 发送推送。"""
        from ai_parenting.backend.channels.base import ChannelMessage
        from ai_parenting.backend.services.push_service import PushResult

        channel_msg = ChannelMessage(
            recipient_id=notification.device_token,  # type: ignore[attr-defined]
            title=notification.title,  # type: ignore[attr-defined]
            body=notification.body,  # type: ignore[attr-defined]
            data=notification.data,  # type: ignore[attr-defined]
        )
        # Legacy PushProvider 只知道 APNs token，直接强制走 APNs
        result = await self._router.route_message(  # type: ignore[attr-defined]
            channel_msg, ["apns"],
        )
        return PushResult(
            success=result.success,
            provider_message_id=result.provider_message_id,
            error=result.error,
        )


@lru_cache(maxsize=1)
def _create_push_provider() -> PushProvider:
    """创建 PushProvider 单例。

    根据配置选择：
    - "channel_router": 桥接到 ChannelRouter（推荐）
    - "mock": MockPushProvider（开发测试）
    """
    if settings.push_provider == "channel_router":
        router = get_channel_router()
        logger.info("PushProvider using ChannelRouter bridge")
        return _ChannelRouterBridge(router)

    # 默认 Mock
    logger.info("PushProvider using MockPushProvider")
    return MockPushProvider()


def get_push_provider() -> PushProvider:
    """FastAPI 依赖：获取 PushProvider 实例。"""
    return _create_push_provider()


# ---------------------------------------------------------------------------
# Channel Router（渠道路由器）
# ---------------------------------------------------------------------------


_channel_router_instance = None


def _create_channel_router():
    """创建 ChannelRouter 单例。

    懒加载模式：仅在首次调用时初始化适配器。
    """
    from ai_parenting.backend.channels.apns_adapter import APNsAdapter
    from ai_parenting.backend.channels.health_monitor import HealthMonitor
    from ai_parenting.backend.channels.openclaw_adapter import OpenClawAdapter
    from ai_parenting.backend.channels.router import ChannelRouter
    from ai_parenting.backend.channels.wechat_adapter import WeChatAdapter

    adapters = []

    # APNs — 始终注册（作为 ultimate fallback）
    apns = APNsAdapter(
        bundle_id=settings.apns_bundle_id,
        key_path=settings.apns_key_path,
        key_id=settings.apns_key_id,
        team_id=settings.apns_team_id,
        use_sandbox=settings.apns_use_sandbox,
    )
    adapters.append(apns)

    # 微信 — 有配置时注册
    if settings.wechat_app_id:
        wechat = WeChatAdapter(
            app_id=settings.wechat_app_id,
            app_secret=settings.wechat_app_secret,
            token=settings.wechat_token,
            aes_key=settings.wechat_aes_key,
        )
        adapters.append(wechat)

    # OpenClaw Gateway — 有配置时注册
    if settings.openclaw_ws_url:
        openclaw = OpenClawAdapter(
            ws_url=settings.openclaw_ws_url,
            api_key=settings.openclaw_api_key,
        )
        adapters.append(openclaw)

    health_monitor = HealthMonitor(adapters=adapters)
    router = ChannelRouter(adapters=adapters, health_monitor=health_monitor)

    logger.info(
        "ChannelRouter initialized with %d adapters: %s",
        len(adapters),
        [a.channel_name for a in adapters],
    )
    return router


def get_channel_router():
    """FastAPI 依赖：获取 ChannelRouter 实例（懒加载单例）。"""
    global _channel_router_instance
    if _channel_router_instance is None:
        _channel_router_instance = _create_channel_router()
    return _channel_router_instance


# ---------------------------------------------------------------------------
# Smart Push Engine
# ---------------------------------------------------------------------------


_push_engine_instance = None


def get_push_engine():
    """FastAPI 依赖：获取 SmartPushEngine 实例（懒加载单例）。

    SmartPushEngine 注入 ChannelRouter 以通过真实渠道推送。
    """
    global _push_engine_instance
    if _push_engine_instance is None:
        from ai_parenting.backend.services.smart_push_engine import SmartPushEngine

        channel_router = get_channel_router()
        _push_engine_instance = SmartPushEngine(channel_router=channel_router)
        logger.info("SmartPushEngine initialized with ChannelRouter")
    return _push_engine_instance
