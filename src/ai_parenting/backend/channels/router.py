"""渠道路由器。

根据用户渠道偏好列表，按优先级选择可用渠道发送消息。
主渠道不可用时自动降级到备选渠道。
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass

from ai_parenting.backend.channels.base import (
    ChannelAdapter,
    ChannelMessage,
    SendResult,
)
from ai_parenting.backend.channels.health_monitor import HealthMonitor

logger = logging.getLogger(__name__)


@dataclass
class RouteDecision:
    """路由决策结果。"""

    selected_channel: str
    attempted_channels: list[str]
    fallback_used: bool = False


class ChannelRouter:
    """渠道路由器。

    核心逻辑：
    1. 接收用户的渠道偏好排序列表（如 ['wechat', 'apns']）
    2. 按优先级遍历，通过 HealthMonitor 检查渠道可用性
    3. 选择首个可用渠道发送消息
    4. 如果首选渠道发送失败，自动降级到下一个可用渠道
    5. 所有渠道均失败时返回最后一个错误
    """

    def __init__(
        self,
        adapters: list[ChannelAdapter],
        health_monitor: HealthMonitor,
    ) -> None:
        self._adapters: dict[str, ChannelAdapter] = {a.channel_name: a for a in adapters}
        self._health_monitor = health_monitor

    @property
    def available_channels(self) -> list[str]:
        """返回所有已注册的渠道名称。"""
        return list(self._adapters.keys())

    def register_adapter(self, adapter: ChannelAdapter) -> None:
        """动态注册渠道适配器。"""
        self._adapters[adapter.channel_name] = adapter
        self._health_monitor.register_adapter(adapter)

    async def route_message(
        self,
        message: ChannelMessage,
        channel_preferences: list[str],
        *,
        force_channel: str | None = None,
    ) -> SendResult:
        """根据渠道偏好列表路由消息。

        Args:
            message: 待发送消息。
            channel_preferences: 用户渠道偏好排序列表，如 ['wechat', 'apns']。
            force_channel: 如果指定，强制使用此渠道（忽略偏好和健康状态）。

        Returns:
            最终发送结果。如果所有渠道均失败，返回最后一个错误结果。
        """
        if force_channel:
            adapter = self._adapters.get(force_channel)
            if adapter is None:
                return SendResult(
                    success=False,
                    channel_name=force_channel,
                    error=f"Channel '{force_channel}' not registered",
                )
            return await self._send_with_timing(adapter, message)

        attempted: list[str] = []
        last_result: SendResult | None = None

        # 按偏好顺序遍历
        for channel_name in channel_preferences:
            adapter = self._adapters.get(channel_name)
            if adapter is None:
                logger.debug("Channel '%s' not registered, skipping", channel_name)
                continue

            if not self._health_monitor.is_available(channel_name):
                logger.info(
                    "Channel '%s' unavailable (health check), skipping",
                    channel_name,
                )
                attempted.append(channel_name)
                continue

            attempted.append(channel_name)
            result = await self._send_with_timing(adapter, message)

            if result.success:
                fallback_used = len(attempted) > 1
                if fallback_used:
                    logger.info(
                        "Message sent via fallback channel '%s' (attempted: %s)",
                        channel_name,
                        attempted,
                    )
                return result

            last_result = result
            logger.warning(
                "Channel '%s' send failed: %s, trying next",
                channel_name,
                result.error,
            )

        # 偏好列表中没有可用渠道时，尝试所有已注册渠道作为最终兜底
        for channel_name, adapter in self._adapters.items():
            if channel_name in attempted:
                continue
            if not self._health_monitor.is_available(channel_name):
                continue

            attempted.append(channel_name)
            result = await self._send_with_timing(adapter, message)
            if result.success:
                logger.info(
                    "Message sent via last-resort channel '%s' (attempted: %s)",
                    channel_name,
                    attempted,
                )
                return result
            last_result = result

        # 全部失败
        if last_result is not None:
            return last_result

        return SendResult(
            success=False,
            channel_name="none",
            error=f"No available channels. Attempted: {attempted}",
        )

    async def _send_with_timing(
        self, adapter: ChannelAdapter, message: ChannelMessage
    ) -> SendResult:
        """发送消息并记录耗时。"""
        start = time.monotonic()
        try:
            result = await adapter.send_message(message)
            result.latency_ms = int((time.monotonic() - start) * 1000)
            return result
        except Exception as exc:
            elapsed = int((time.monotonic() - start) * 1000)
            logger.error(
                "Channel '%s' send exception: %s (latency=%dms)",
                adapter.channel_name,
                exc,
                elapsed,
            )
            return SendResult(
                success=False,
                channel_name=adapter.channel_name,
                error=str(exc),
                latency_ms=elapsed,
            )

    async def close_all(self) -> None:
        """关闭所有渠道适配器的连接。"""
        for adapter in self._adapters.values():
            try:
                await adapter.close()
            except Exception as exc:
                logger.error("Error closing channel '%s': %s", adapter.channel_name, exc)
