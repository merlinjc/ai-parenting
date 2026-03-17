"""渠道适配器模块。

提供 ChannelAdapter 抽象层、ChannelRouter 路由降级策略、
HealthMonitor 渠道健康探测，以及 APNs/WeChat/OpenClaw 三个适配器实现。
"""

from ai_parenting.backend.channels.base import (
    ChannelAdapter,
    ChannelHealth,
    ChannelMessage,
    ChannelStatus,
    InboundMessage,
    SendResult,
)
from ai_parenting.backend.channels.health_monitor import HealthMonitor
from ai_parenting.backend.channels.router import ChannelRouter

__all__ = [
    "ChannelAdapter",
    "ChannelHealth",
    "ChannelMessage",
    "ChannelRouter",
    "ChannelStatus",
    "HealthMonitor",
    "InboundMessage",
    "SendResult",
]
