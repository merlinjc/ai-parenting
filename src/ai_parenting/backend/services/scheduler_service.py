"""定时推送调度服务。

提供定时任务提醒、记录提示等推送相关的业务逻辑函数，
由 scheduler.py 中的定时任务调用。
"""

from __future__ import annotations

import logging
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ai_parenting.backend.models import Child, DayTask, Plan, User
from ai_parenting.backend.services.message_service import create_message
from ai_parenting.backend.services.push_service import (
    MockPushProvider,
    send_push_for_message,
)

logger = logging.getLogger(__name__)


async def send_daily_task_reminders(db: AsyncSession) -> int:
    """发送每日任务提醒消息。

    遍历所有活跃计划，为每个计划的 User 创建 plan_reminder 消息。

    Returns:
        发送的提醒数量。
    """
    # 查询所有活跃计划及其关联的 child → user
    result = await db.execute(
        select(Plan, Child, User)
        .join(Child, Plan.child_id == Child.id)
        .join(User, Child.user_id == User.id)
        .where(Plan.status == "active", User.push_enabled.is_(True))
    )
    rows = result.all()

    sent_count = 0
    push_provider = MockPushProvider()  # 使用 Mock 推送，后续可替换

    for plan, child, user in rows:
        # 获取今日任务
        today_task: DayTask | None = None
        for task in plan.day_tasks:
            if task.day_number == plan.current_day:
                today_task = task
                break

        task_title = today_task.main_exercise_title if today_task else "今日任务"

        message = await create_message(
            db,
            user_id=user.id,
            child_id=child.id,
            message_type="plan_reminder",
            target_params={"plan_id": str(plan.id)},
            body_override=f"今天是{child.nickname}的第 {plan.current_day} 天：「{task_title}」，点击查看详情。",
            summary_override=f"Day {plan.current_day}：{task_title}",
        )
        await send_push_for_message(db, message, push_provider)
        sent_count += 1

    logger.info("Sent %d daily task reminders", sent_count)
    return sent_count


async def send_record_prompts(db: AsyncSession) -> int:
    """发送记录提示消息。

    遍历所有活跃计划，为每个计划的 User 创建 record_prompt 消息。

    Returns:
        发送的提示数量。
    """
    result = await db.execute(
        select(Plan, Child, User)
        .join(Child, Plan.child_id == Child.id)
        .join(User, Child.user_id == User.id)
        .where(Plan.status == "active", User.push_enabled.is_(True))
    )
    rows = result.all()

    sent_count = 0
    push_provider = MockPushProvider()

    for plan, child, user in rows:
        message = await create_message(
            db,
            user_id=user.id,
            child_id=child.id,
            message_type="record_prompt",
            target_params={"child_id": str(child.id)},
            body_override=f"今天和{child.nickname}的互动还不错吗？花 1 分钟记录一下观察到的变化吧。",
        )
        await send_push_for_message(db, message, push_provider)
        sent_count += 1

    logger.info("Sent %d record prompts", sent_count)
    return sent_count


async def send_plan_expiry_reminder(db: AsyncSession) -> int:
    """发送计划到期提醒（第 6 天提醒周反馈即将生成）。

    Returns:
        发送的提醒数量。
    """
    # 查找 current_day == 6 的活跃计划
    result = await db.execute(
        select(Plan, Child, User)
        .join(Child, Plan.child_id == Child.id)
        .join(User, Child.user_id == User.id)
        .where(Plan.status == "active", Plan.current_day == 6, User.push_enabled.is_(True))
    )
    rows = result.all()

    sent_count = 0
    push_provider = MockPushProvider()

    for plan, child, user in rows:
        message = await create_message(
            db,
            user_id=user.id,
            child_id=child.id,
            message_type="plan_reminder",
            target_params={"plan_id": str(plan.id)},
            title_override="本周计划即将结束",
            body_override=f"{child.nickname}的本周微计划明天到期，周反馈将在明日自动生成。",
            summary_override="明日将生成本周反馈报告",
        )
        await send_push_for_message(db, message, push_provider)
        sent_count += 1

    logger.info("Sent %d plan expiry reminders", sent_count)
    return sent_count
