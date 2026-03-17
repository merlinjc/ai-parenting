"""推送服务。

提供 PushProvider 抽象接口和 MockPushProvider 测试实现。
推送调度逻辑通过 send_push() 协调消息推送和状态更新。
"""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ai_parenting.backend.models import Device, Message


@dataclass
class PushNotification:
    """推送通知载体。"""

    device_token: str
    title: str
    body: str
    data: dict[str, str] | None = None


@dataclass
class PushResult:
    """推送结果。"""

    success: bool
    provider_message_id: str | None = None
    error: str | None = None


class PushProvider(ABC):
    """推送服务抽象基类，类似 ModelProvider 模式。"""

    @abstractmethod
    async def send_notification(self, notification: PushNotification) -> PushResult:
        """发送一条推送通知。"""
        ...


class MockPushProvider(PushProvider):
    """测试用 Mock 推送实现，记录所有调用参数。"""

    def __init__(self) -> None:
        self.sent: list[PushNotification] = []

    async def send_notification(self, notification: PushNotification) -> PushResult:
        self.sent.append(notification)
        return PushResult(success=True, provider_message_id=f"mock-{uuid.uuid4().hex[:8]}")


async def send_push_for_message(
    db: AsyncSession,
    message: Message,
    push_provider: PushProvider,
) -> None:
    """为消息发送推送通知。

    查找用户的活跃设备，向每个设备发送推送。
    更新消息的 push_status 和 push_sent_at。
    """
    # 查找用户的活跃设备
    stmt = select(Device).where(
        Device.user_id == message.user_id,
        Device.is_active.is_(True),
        Device.push_token.isnot(None),
    )
    result = await db.execute(stmt)
    devices = result.scalars().all()

    if not devices:
        message.push_status = "skipped"  # P2-10: 无设备标记为 skipped（而非 sent）
        message.push_sent_at = datetime.now(timezone.utc)
        return

    any_success = False
    last_error = None

    for device in devices:
        notification = PushNotification(
            device_token=device.push_token,
            title=message.title,
            body=message.summary,
            data={
                "message_id": str(message.id),
                "type": message.type,
                "target_page": message.target_page or "",
            },
        )
        try:
            push_result = await push_provider.send_notification(notification)
            if push_result.success:
                any_success = True
            else:
                last_error = push_result.error
        except Exception as exc:
            last_error = str(exc)

    now = datetime.now(timezone.utc)
    if any_success:
        message.push_status = "sent"
        message.push_sent_at = now
    else:
        message.push_status = "failed"
        message.push_sent_at = now
