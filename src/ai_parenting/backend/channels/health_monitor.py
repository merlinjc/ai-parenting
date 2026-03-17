"""渠道健康监控。

定期探测所有注册渠道的健康状态，维护可用性状态缓存，
供 ChannelRouter 在路由决策时快速查询渠道可用性。
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

from ai_parenting.backend.channels.base import (
    ChannelAdapter,
    ChannelHealth,
    ChannelStatus,
)

logger = logging.getLogger(__name__)

# 默认探测间隔 60 秒
DEFAULT_CHECK_INTERVAL = 60

# 连续失败达到此阈值则标记为 UNAVAILABLE
FAILURE_THRESHOLD = 3


class HealthMonitor:
    """渠道健康监控器。

    后台 asyncio Task 定期探测每个渠道的健康状态，
    维护 {channel_name: ChannelHealth} 状态字典。
    """

    def __init__(
        self,
        adapters: list[ChannelAdapter],
        check_interval: int = DEFAULT_CHECK_INTERVAL,
    ) -> None:
        self._adapters: dict[str, ChannelAdapter] = {a.channel_name: a for a in adapters}
        self._check_interval = check_interval
        self._health_cache: dict[str, ChannelHealth] = {}
        self._failure_counts: dict[str, int] = {}
        self._task: asyncio.Task | None = None

    @property
    def health_cache(self) -> dict[str, ChannelHealth]:
        """获取当前渠道健康状态缓存的只读副本。"""
        return dict(self._health_cache)

    def get_status(self, channel_name: str) -> ChannelHealth | None:
        """查询指定渠道的最近一次健康状态。"""
        return self._health_cache.get(channel_name)

    def is_available(self, channel_name: str) -> bool:
        """判断渠道是否可用（HEALTHY 或 DEGRADED 均视为可用）。"""
        health = self._health_cache.get(channel_name)
        if health is None:
            return True  # 未检测过，乐观假设可用
        return health.status != ChannelStatus.UNAVAILABLE

    def register_adapter(self, adapter: ChannelAdapter) -> None:
        """动态注册新的渠道适配器。"""
        self._adapters[adapter.channel_name] = adapter

    def unregister_adapter(self, channel_name: str) -> None:
        """注销渠道适配器。"""
        self._adapters.pop(channel_name, None)
        self._health_cache.pop(channel_name, None)
        self._failure_counts.pop(channel_name, None)

    def start(self) -> None:
        """启动后台健康探测任务。"""
        if self._task is not None and not self._task.done():
            logger.warning("HealthMonitor already running, skipping start")
            return
        self._task = asyncio.create_task(self._monitor_loop())
        logger.info(
            "HealthMonitor started: %d adapters, interval=%ds",
            len(self._adapters),
            self._check_interval,
        )

    def stop(self) -> None:
        """停止后台健康探测任务。"""
        if self._task is not None:
            self._task.cancel()
            self._task = None
            logger.info("HealthMonitor stopped")

    async def check_all(self) -> dict[str, ChannelHealth]:
        """立即执行一次全渠道健康检查（手动触发）。"""
        results: dict[str, ChannelHealth] = {}
        tasks = {name: adapter.health_check() for name, adapter in self._adapters.items()}

        for name, coro in tasks.items():
            try:
                health = await asyncio.wait_for(coro, timeout=10.0)
                self._on_check_result(name, health)
                results[name] = health
            except asyncio.TimeoutError:
                health = ChannelHealth(
                    status=ChannelStatus.DEGRADED,
                    error="Health check timeout (>10s)",
                    last_check_at=datetime.now(timezone.utc),
                )
                self._on_check_result(name, health)
                results[name] = health
            except Exception as exc:
                health = ChannelHealth(
                    status=ChannelStatus.UNAVAILABLE,
                    error=str(exc),
                    last_check_at=datetime.now(timezone.utc),
                )
                self._on_check_result(name, health)
                results[name] = health

        return results

    async def _monitor_loop(self) -> None:
        """后台监控循环。"""
        while True:
            try:
                await self.check_all()
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.error("HealthMonitor loop error: %s", exc)
            await asyncio.sleep(self._check_interval)

    def _on_check_result(self, channel_name: str, health: ChannelHealth) -> None:
        """处理单次检查结果，更新缓存和失败计数。"""
        if health.status == ChannelStatus.HEALTHY:
            self._failure_counts[channel_name] = 0
        else:
            count = self._failure_counts.get(channel_name, 0) + 1
            self._failure_counts[channel_name] = count

            if count >= FAILURE_THRESHOLD and health.status != ChannelStatus.UNAVAILABLE:
                health = ChannelHealth(
                    status=ChannelStatus.UNAVAILABLE,
                    error=f"Consecutive failures: {count} (threshold: {FAILURE_THRESHOLD})",
                    last_check_at=health.last_check_at,
                    latency_ms=health.latency_ms,
                )
                logger.warning(
                    "Channel '%s' marked UNAVAILABLE after %d failures",
                    channel_name,
                    count,
                )

        self._health_cache[channel_name] = health
