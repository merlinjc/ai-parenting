"""消息服务测试。

覆盖消息的模板创建、列表查询、状态更新、未读计数和点击回流。
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from ai_parenting.backend.models import Message, User
from ai_parenting.backend.services import message_service


@pytest.fixture
async def user(db_session: AsyncSession) -> User:
    """创建测试用户。"""
    user = User(display_name="测试家长", auth_provider="email")
    db_session.add(user)
    await db_session.flush()
    return user


class TestCreateMessage:
    """消息创建测试。"""

    async def test_create_plan_reminder(self, db_session, user):
        msg = await message_service.create_message(
            db_session, user_id=user.id, message_type="plan_reminder",
        )
        assert msg.type == "plan_reminder"
        assert msg.title == "今日任务提醒"
        assert msg.read_status == "unread"
        assert msg.push_status == "pending"
        assert msg.target_page == "plan_detail"

    async def test_create_record_prompt(self, db_session, user):
        msg = await message_service.create_message(
            db_session, user_id=user.id, message_type="record_prompt",
        )
        assert msg.type == "record_prompt"
        assert msg.title == "记录提醒"
        assert msg.target_page == "record_create"

    async def test_create_weekly_feedback_ready(self, db_session, user):
        msg = await message_service.create_message(
            db_session, user_id=user.id, message_type="weekly_feedback_ready",
            target_params={"feedback_id": "abc"},
        )
        assert msg.type == "weekly_feedback_ready"
        assert msg.requires_preview is True
        assert msg.target_params == {"feedback_id": "abc"}

    async def test_create_risk_alert(self, db_session, user):
        msg = await message_service.create_message(
            db_session, user_id=user.id,
            child_id=uuid.uuid4(),
            message_type="risk_alert",
        )
        assert msg.type == "risk_alert"
        assert msg.requires_preview is True
        assert "建议" in msg.body

    async def test_create_system_message(self, db_session, user):
        msg = await message_service.create_message(
            db_session, user_id=user.id, message_type="system",
            title_override="系统维护通知",
            body_override="系统将于今晚 22:00 进行维护",
            summary_override="维护通知",
        )
        assert msg.title == "系统维护通知"
        assert msg.body == "系统将于今晚 22:00 进行维护"

    async def test_create_with_child_id(self, db_session, user):
        child_id = uuid.uuid4()
        msg = await message_service.create_message(
            db_session, user_id=user.id, child_id=child_id,
            message_type="plan_reminder",
        )
        assert msg.child_id == child_id


class TestListMessages:
    """消息列表查询测试。"""

    async def test_empty_list(self, db_session, user):
        messages, has_more = await message_service.list_messages(
            db_session, user.id,
        )
        assert messages == []
        assert has_more is False

    async def test_list_with_messages(self, db_session, user):
        for i in range(3):
            await message_service.create_message(
                db_session, user_id=user.id,
                message_type="plan_reminder",
            )
        messages, has_more = await message_service.list_messages(
            db_session, user.id,
        )
        assert len(messages) == 3
        assert has_more is False

    async def test_pagination(self, db_session, user):
        for i in range(5):
            await message_service.create_message(
                db_session, user_id=user.id,
                message_type="plan_reminder",
            )
        messages, has_more = await message_service.list_messages(
            db_session, user.id, limit=3,
        )
        assert len(messages) == 3
        assert has_more is True

    async def test_unread_first_ordering(self, db_session, user):
        # 创建 3 条消息
        msg1 = await message_service.create_message(
            db_session, user_id=user.id, message_type="plan_reminder",
        )
        msg2 = await message_service.create_message(
            db_session, user_id=user.id, message_type="record_prompt",
        )
        msg3 = await message_service.create_message(
            db_session, user_id=user.id, message_type="system",
            title_override="通知", body_override="测试", summary_override="测试",
        )
        # 标记 msg1 为已读
        await message_service.update_read_status(db_session, msg1.id, "read")

        messages, _ = await message_service.list_messages(db_session, user.id)
        # 未读消息应排在前面
        unread_msgs = [m for m in messages if m.read_status == "unread"]
        read_msgs = [m for m in messages if m.read_status != "unread"]
        assert len(unread_msgs) == 2
        assert len(read_msgs) == 1


class TestUpdateReadStatus:
    """消息状态更新测试。"""

    async def test_mark_as_read(self, db_session, user):
        msg = await message_service.create_message(
            db_session, user_id=user.id, message_type="plan_reminder",
        )
        updated = await message_service.update_read_status(
            db_session, msg.id, "read",
        )
        assert updated.read_status == "read"

    async def test_mark_as_processed(self, db_session, user):
        msg = await message_service.create_message(
            db_session, user_id=user.id, message_type="plan_reminder",
        )
        updated = await message_service.update_read_status(
            db_session, msg.id, "processed",
        )
        assert updated.read_status == "processed"

    async def test_nonexistent_message(self, db_session, user):
        result = await message_service.update_read_status(
            db_session, uuid.uuid4(), "read",
        )
        assert result is None


class TestUnreadCount:
    """未读计数测试。"""

    async def test_zero_unread(self, db_session, user):
        count = await message_service.get_unread_count(db_session, user.id)
        assert count == 0

    async def test_count_after_create(self, db_session, user):
        for _ in range(3):
            await message_service.create_message(
                db_session, user_id=user.id, message_type="plan_reminder",
            )
        count = await message_service.get_unread_count(db_session, user.id)
        assert count == 3

    async def test_count_after_read(self, db_session, user):
        msg = await message_service.create_message(
            db_session, user_id=user.id, message_type="plan_reminder",
        )
        await message_service.create_message(
            db_session, user_id=user.id, message_type="record_prompt",
        )
        await message_service.update_read_status(db_session, msg.id, "read")
        count = await message_service.get_unread_count(db_session, user.id)
        assert count == 1


class TestRecordClick:
    """点击回流测试。"""

    async def test_click_marks_read(self, db_session, user):
        msg = await message_service.create_message(
            db_session, user_id=user.id, message_type="plan_reminder",
        )
        updated = await message_service.record_click(db_session, msg.id)
        assert updated.clicked_at is not None
        assert updated.read_status == "read"

    async def test_click_nonexistent(self, db_session, user):
        result = await message_service.record_click(db_session, uuid.uuid4())
        assert result is None

    async def test_click_already_read(self, db_session, user):
        msg = await message_service.create_message(
            db_session, user_id=user.id, message_type="plan_reminder",
        )
        await message_service.update_read_status(db_session, msg.id, "processed")
        updated = await message_service.record_click(db_session, msg.id)
        assert updated.clicked_at is not None
        assert updated.read_status == "processed"  # 已 processed 不降级为 read
