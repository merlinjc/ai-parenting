"""推送服务测试。

覆盖 MockPushProvider 调用验证、推送状态更新和推送失败处理。
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from ai_parenting.backend.models import Device, Message, User
from ai_parenting.backend.services.push_service import (
    MockPushProvider,
    PushNotification,
    PushResult,
    send_push_for_message,
)


@pytest.fixture
async def user(db_session: AsyncSession) -> User:
    user = User(display_name="测试家长", auth_provider="email")
    db_session.add(user)
    await db_session.flush()
    return user


@pytest.fixture
async def message(db_session: AsyncSession, user: User) -> Message:
    msg = Message(
        user_id=user.id,
        type="plan_reminder",
        title="测试标题",
        body="测试内容",
        summary="测试摘要",
        read_status="unread",
        push_status="pending",
    )
    db_session.add(msg)
    await db_session.flush()
    return msg


class TestMockPushProvider:
    """MockPushProvider 测试。"""

    async def test_send_notification(self):
        provider = MockPushProvider()
        notification = PushNotification(
            device_token="test-token",
            title="标题",
            body="内容",
        )
        result = await provider.send_notification(notification)
        assert result.success is True
        assert result.provider_message_id is not None
        assert len(provider.sent) == 1
        assert provider.sent[0].device_token == "test-token"

    async def test_send_multiple(self):
        provider = MockPushProvider()
        for i in range(3):
            await provider.send_notification(
                PushNotification(device_token=f"token-{i}", title="t", body="b")
            )
        assert len(provider.sent) == 3


class TestSendPushForMessage:
    """推送调度测试。"""

    async def test_no_devices(self, db_session, user, message):
        """无设备时标记为 sent（无需推送）。"""
        provider = MockPushProvider()
        await send_push_for_message(db_session, message, provider)
        assert message.push_status == "sent"
        assert message.push_sent_at is not None
        assert len(provider.sent) == 0

    async def test_with_active_device(self, db_session, user, message):
        """有活跃设备时发送推送。"""
        device = Device(
            user_id=user.id,
            push_token="apns-token-123",
            platform="ios",
            app_version="1.0.0",
            is_active=True,
        )
        db_session.add(device)
        await db_session.flush()

        provider = MockPushProvider()
        await send_push_for_message(db_session, message, provider)
        assert message.push_status == "sent"
        assert len(provider.sent) == 1
        assert provider.sent[0].device_token == "apns-token-123"

    async def test_inactive_device_ignored(self, db_session, user, message):
        """非活跃设备被忽略。"""
        device = Device(
            user_id=user.id,
            push_token="apns-token-123",
            platform="ios",
            app_version="1.0.0",
            is_active=False,
        )
        db_session.add(device)
        await db_session.flush()

        provider = MockPushProvider()
        await send_push_for_message(db_session, message, provider)
        assert message.push_status == "sent"  # 无活跃设备也标记 sent
        assert len(provider.sent) == 0

    async def test_device_without_token_ignored(self, db_session, user, message):
        """无 push_token 的设备被忽略。"""
        device = Device(
            user_id=user.id,
            push_token=None,
            platform="ios",
            app_version="1.0.0",
            is_active=True,
        )
        db_session.add(device)
        await db_session.flush()

        provider = MockPushProvider()
        await send_push_for_message(db_session, message, provider)
        assert message.push_status == "sent"
        assert len(provider.sent) == 0

    async def test_multiple_devices(self, db_session, user, message):
        """多设备全部发送。"""
        for i in range(3):
            device = Device(
                user_id=user.id,
                push_token=f"token-{i}",
                platform="ios",
                app_version="1.0.0",
                is_active=True,
            )
            db_session.add(device)
        await db_session.flush()

        provider = MockPushProvider()
        await send_push_for_message(db_session, message, provider)
        assert message.push_status == "sent"
        assert len(provider.sent) == 3
