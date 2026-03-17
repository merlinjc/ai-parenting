"""消息服务。

提供消息的模板化创建、列表查询（分页+未处理优先排序）、
状态更新、未读计数和点击回流功能。

消息创建为内部服务调用（非公开 API），供周反馈、风险升级等模块使用。
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ai_parenting.backend.models import Message


# ---------------------------------------------------------------------------
# 消息模板系统
# ---------------------------------------------------------------------------

MESSAGE_TEMPLATES: dict[str, dict[str, Any]] = {
    "plan_reminder": {
        "title": "今日任务提醒",
        "body": "今天的亲子互动任务已准备好，点击查看详情并开始执行。",
        "summary": "今天的任务已准备就绪",
        "target_page": "plan_detail",
        "requires_preview": False,
    },
    "record_prompt": {
        "title": "记录提醒",
        "body": "今天和宝宝的互动还不错吗？花 1 分钟记录一下观察到的变化吧。",
        "summary": "别忘了记录今天的观察",
        "target_page": "record_create",
        "requires_preview": False,
    },
    "weekly_feedback_ready": {
        "title": "本周反馈已生成",
        "body": "本周的亲子互动反馈报告已经准备好了，快来看看宝宝这周的成长变化吧！",
        "summary": "本周反馈报告已就绪",
        "target_page": "weekly_feedback_detail",
        "requires_preview": True,
    },
    "risk_alert": {
        "title": "成长关注提醒",
        "body": "根据最近的观察记录，我们建议您关注宝宝的某些发展表现。这不代表存在问题，但建议在下次体检时与医生沟通。",
        "summary": "建议关注宝宝的成长发展",
        "target_page": "child_profile",
        "requires_preview": True,
    },
    "system": {
        "title": "系统通知",
        "body": "",
        "summary": "",
        "target_page": None,
        "requires_preview": False,
    },
}


async def create_message(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    child_id: uuid.UUID | None = None,
    message_type: str,
    target_params: dict[str, str] | None = None,
    title_override: str | None = None,
    body_override: str | None = None,
    summary_override: str | None = None,
) -> Message:
    """使用模板创建消息。

    支持通过 override 参数覆盖模板默认文本。
    """
    template = MESSAGE_TEMPLATES.get(message_type, MESSAGE_TEMPLATES["system"])

    message = Message(
        user_id=user_id,
        child_id=child_id,
        type=message_type,
        title=title_override or template["title"],
        body=body_override or template["body"],
        summary=summary_override or template["summary"],
        target_page=template["target_page"],
        target_params=target_params,
        requires_preview=template["requires_preview"],
        read_status="unread",
        push_status="pending",
    )
    db.add(message)
    await db.flush()
    return message


async def list_messages(
    db: AsyncSession,
    user_id: uuid.UUID,
    *,
    limit: int = 20,
    before: datetime | None = None,
) -> tuple[list[Message], bool]:
    """查询消息列表（分页，未处理优先排序）。

    返回 (messages, has_more) 元组。
    排序规则：unread 优先，然后按 created_at 降序。
    """
    stmt = select(Message).where(Message.user_id == user_id)
    if before:
        stmt = stmt.where(Message.created_at < before)

    # 未读优先，然后按创建时间降序
    stmt = stmt.order_by(
        # unread 排在最前
        (Message.read_status != "unread"),
        Message.created_at.desc(),
    ).limit(limit + 1)

    result = await db.execute(stmt)
    messages = list(result.scalars().all())

    has_more = len(messages) > limit
    if has_more:
        messages = messages[:limit]

    return messages, has_more


async def get_message(
    db: AsyncSession,
    message_id: uuid.UUID,
) -> Message | None:
    """获取单条消息。"""
    return await db.get(Message, message_id)


async def update_read_status(
    db: AsyncSession,
    message_id: uuid.UUID,
    read_status: str,
) -> Message | None:
    """更新消息阅读状态。"""
    # P2-4: read_status 白名单校验
    if read_status not in ("unread", "read"):
        raise ValueError(f"Invalid read_status: {read_status}. Must be 'unread' or 'read'")
    message = await db.get(Message, message_id)
    if message is None:
        return None
    message.read_status = read_status
    await db.flush()
    return message


async def get_unread_count(
    db: AsyncSession,
    user_id: uuid.UUID,
) -> int:
    """获取用户未读消息计数。"""
    stmt = select(func.count()).select_from(Message).where(
        Message.user_id == user_id,
        Message.read_status == "unread",
    )
    result = await db.execute(stmt)
    return result.scalar_one()


async def record_click(
    db: AsyncSession,
    message_id: uuid.UUID,
) -> Message | None:
    """记录消息点击事件。"""
    message = await db.get(Message, message_id)
    if message is None:
        return None
    message.clicked_at = datetime.now(timezone.utc)
    if message.read_status == "unread":
        message.read_status = "read"
    await db.flush()
    return message
