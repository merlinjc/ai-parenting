"""定时推送调度服务。

提供定时任务提醒、记录提示等推送相关的业务逻辑函数，
由 scheduler.py 中的定时任务调用。

重构说明（2.0）：
- MockPushProvider 不再硬编码，改为参数注入（默认仍为 Mock）
- 查询改为游标分页，每批 100 条，避免全量加载
- 新增 send_plan_expiry_reminder 完整实现
- Smart 模式下这些函数仅作为 Legacy 兜底，推荐使用 SmartPushEngine
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
    PushProvider,
    send_push_for_message,
)

logger = logging.getLogger(__name__)

# 每批处理的记录数（游标分页）
_BATCH_SIZE = 100


def _get_default_push_provider() -> PushProvider:
    """获取默认推送提供者。

    后续可通过配置切换到真实 APNs/ChannelRouter。
    """
    return MockPushProvider()


async def send_daily_task_reminders(
    db: AsyncSession,
    push_provider: PushProvider | None = None,
) -> int:
    """发送每日任务提醒消息。

    采用游标分页遍历所有活跃计划，为每个计划的 User 创建 plan_reminder 消息。

    Args:
        db: 数据库会话。
        push_provider: 推送提供者（默认 MockPushProvider）。

    Returns:
        发送的提醒数量。
    """
    provider = push_provider or _get_default_push_provider()
    sent_count = 0
    last_plan_id: uuid.UUID | None = None

    while True:
        stmt = (
            select(Plan, Child, User)
            .join(Child, Plan.child_id == Child.id)
            .join(User, Child.user_id == User.id)
            .where(Plan.status == "active", User.push_enabled.is_(True))
            .order_by(Plan.id)
            .limit(_BATCH_SIZE)
        )
        if last_plan_id is not None:
            stmt = stmt.where(Plan.id > last_plan_id)

        result = await db.execute(stmt)
        rows = result.all()

        if not rows:
            break

        for plan, child, user in rows:
            last_plan_id = plan.id

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
                body_override=(
                    f"今天是{child.nickname}的第 {plan.current_day} 天："
                    f"「{task_title}」，点击查看详情。"
                ),
                summary_override=f"Day {plan.current_day}：{task_title}",
            )
            await send_push_for_message(db, message, provider)
            sent_count += 1

        # 如果本批不足 _BATCH_SIZE，说明已经是最后一批
        if len(rows) < _BATCH_SIZE:
            break

    logger.info("Sent %d daily task reminders", sent_count)
    return sent_count


async def send_record_prompts(
    db: AsyncSession,
    push_provider: PushProvider | None = None,
) -> int:
    """发送记录提示消息。

    采用游标分页遍历所有活跃计划，为每个计划的 User 创建 record_prompt 消息。

    Args:
        db: 数据库会话。
        push_provider: 推送提供者（默认 MockPushProvider）。

    Returns:
        发送的提示数量。
    """
    provider = push_provider or _get_default_push_provider()
    sent_count = 0
    last_plan_id: uuid.UUID | None = None

    while True:
        stmt = (
            select(Plan, Child, User)
            .join(Child, Plan.child_id == Child.id)
            .join(User, Child.user_id == User.id)
            .where(Plan.status == "active", User.push_enabled.is_(True))
            .order_by(Plan.id)
            .limit(_BATCH_SIZE)
        )
        if last_plan_id is not None:
            stmt = stmt.where(Plan.id > last_plan_id)

        result = await db.execute(stmt)
        rows = result.all()

        if not rows:
            break

        for plan, child, user in rows:
            last_plan_id = plan.id

            message = await create_message(
                db,
                user_id=user.id,
                child_id=child.id,
                message_type="record_prompt",
                target_params={"child_id": str(child.id)},
                body_override=(
                    f"今天和{child.nickname}的互动还不错吗？"
                    f"花 1 分钟记录一下观察到的变化吧。"
                ),
            )
            await send_push_for_message(db, message, provider)
            sent_count += 1

        if len(rows) < _BATCH_SIZE:
            break

    logger.info("Sent %d record prompts", sent_count)
    return sent_count


async def send_plan_expiry_reminder(
    db: AsyncSession,
    push_provider: PushProvider | None = None,
) -> int:
    """发送计划到期提醒（第 6 天提醒周反馈即将生成）。

    Args:
        db: 数据库会话。
        push_provider: 推送提供者（默认 MockPushProvider）。

    Returns:
        发送的提醒数量。
    """
    provider = push_provider or _get_default_push_provider()
    sent_count = 0
    last_plan_id: uuid.UUID | None = None

    while True:
        stmt = (
            select(Plan, Child, User)
            .join(Child, Plan.child_id == Child.id)
            .join(User, Child.user_id == User.id)
            .where(
                Plan.status == "active",
                Plan.current_day == 6,
                User.push_enabled.is_(True),
            )
            .order_by(Plan.id)
            .limit(_BATCH_SIZE)
        )
        if last_plan_id is not None:
            stmt = stmt.where(Plan.id > last_plan_id)

        result = await db.execute(stmt)
        rows = result.all()

        if not rows:
            break

        for plan, child, user in rows:
            last_plan_id = plan.id

            message = await create_message(
                db,
                user_id=user.id,
                child_id=child.id,
                message_type="plan_reminder",
                target_params={"plan_id": str(plan.id)},
                title_override="本周计划即将结束",
                body_override=(
                    f"{child.nickname}的本周微计划明天到期，"
                    f"周反馈将在明日自动生成。"
                ),
                summary_override="明日将生成本周反馈报告",
            )
            await send_push_for_message(db, message, provider)
            sent_count += 1

        if len(rows) < _BATCH_SIZE:
            break

    logger.info("Sent %d plan expiry reminders", sent_count)
    return sent_count
