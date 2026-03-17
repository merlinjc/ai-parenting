"""渠道适配器抽象基类。

定义统一的渠道适配器接口，包含消息收发、健康检查和限流状态查询。
所有渠道实现（APNs、微信、OpenClaw 等）均需实现此接口。
"""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class ChannelStatus(Enum):
    """渠道健康状态。"""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"


class MessageType(Enum):
    """消息类型。"""

    TEXT = "text"
    TEMPLATE = "template"
    RICH = "rich"
    VOICE = "voice"


@dataclass
class ChannelMessage:
    """出站消息载体。"""

    recipient_id: str
    title: str
    body: str
    message_type: MessageType = MessageType.TEXT
    template_id: str | None = None
    template_data: dict[str, Any] | None = None
    data: dict[str, str] | None = None
    idempotency_key: str | None = None

    def __post_init__(self) -> None:
        if self.idempotency_key is None:
            self.idempotency_key = uuid.uuid4().hex


@dataclass
class SendResult:
    """消息发送结果。"""

    success: bool
    channel_name: str
    provider_message_id: str | None = None
    error: str | None = None
    latency_ms: int | None = None
    sent_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class InboundMessage:
    """入站消息（来自外部渠道的用户消息）。"""

    channel_name: str
    sender_id: str
    content: str
    message_type: MessageType = MessageType.TEXT
    raw_payload: dict[str, Any] | None = None
    received_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class ChannelHealth:
    """渠道健康状态报告。"""

    status: ChannelStatus
    latency_ms: int | None = None
    last_check_at: datetime | None = None
    error: str | None = None
    metadata: dict[str, Any] | None = None


class ChannelAdapter(ABC):
    """渠道适配器抽象基类。

    所有渠道实现（APNs、微信公众号、OpenClaw Gateway 等）
    均需继承此类并实现以下抽象方法。

    设计原则：
    - send_message / receive_message：核心收发能力
    - health_check：运维可观测性，供 HealthMonitor 定期探测
    - get_rate_limit_status：限流感知，供 ChannelRouter 做渠道选择
    """

    @property
    @abstractmethod
    def channel_name(self) -> str:
        """渠道唯一标识，如 'apns'、'wechat'、'openclaw_whatsapp'。"""
        ...

    @abstractmethod
    async def send_message(self, message: ChannelMessage) -> SendResult:
        """发送一条消息到此渠道。

        Args:
            message: 待发送的消息载体。

        Returns:
            发送结果，包含成功/失败状态和渠道侧消息 ID。
        """
        ...

    @abstractmethod
    async def receive_message(self, raw_payload: dict[str, Any]) -> InboundMessage | None:
        """解析入站消息原始载荷。

        Args:
            raw_payload: 渠道回调推送的原始 JSON。

        Returns:
            解析后的 InboundMessage，如果载荷无法识别则返回 None。
        """
        ...

    @abstractmethod
    async def health_check(self) -> ChannelHealth:
        """执行一次渠道健康探测。

        由 HealthMonitor 定期调用，返回当前渠道的可用状态和延迟。
        """
        ...

    async def get_rate_limit_status(self) -> dict[str, int]:
        """返回当前渠道的限流配额状态。

        Returns:
            包含 'remaining'（剩余配额）和 'limit'（总配额）的字典。
            默认实现返回空字典（表示不支持限流查询）。
        """
        return {}

    async def close(self) -> None:
        """释放渠道连接资源。

        默认空实现，子类按需覆盖（如关闭 WebSocket 连接）。
        """
        pass
