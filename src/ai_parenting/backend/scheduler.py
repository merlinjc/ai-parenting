"""定时任务调度器。

使用 APScheduler 管理定时任务：
- 每日零点推进计划 current_day
- 每日 08:00 发送任务提醒
- 每日 18:00 发送记录提示
"""

from __future__ import annotations

import logging
from datetime import timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from ai_parenting.backend.database import async_session_factory

logger = logging.getLogger(__name__)

_scheduler: AsyncIOScheduler | None = None


async def _advance_plans_job() -> None:
    """每日零点推进所有活跃计划的 current_day。"""
    from ai_parenting.backend.services.plan_service import advance_all_plans

    logger.info("Running daily plan advancement job...")
    async with async_session_factory() as session:
        try:
            result = await advance_all_plans(session)
            await session.commit()
            logger.info("Plan advancement completed: %s", result)

            # 对推进到第 7 天的计划自动触发周反馈（Gap 10）
            plans_day7 = result.get("plans_reaching_day7", [])
            if plans_day7:
                await _trigger_weekly_feedbacks(plans_day7)
        except Exception:
            await session.rollback()
            logger.exception("Plan advancement job failed")


async def _trigger_weekly_feedbacks(plans: list) -> None:
    """对推进到第 7 天的计划自动生成周反馈。"""
    from ai_parenting.backend.services import weekly_feedback_service

    for plan in plans:
        try:
            async with async_session_factory() as session:
                feedback = await weekly_feedback_service.create_weekly_feedback(
                    db=session,
                    plan_id=plan.id,
                )
                await session.commit()
                logger.info(
                    "Auto-generated weekly feedback for plan %s: feedback_id=%s",
                    plan.id,
                    feedback.id if feedback else "None",
                )
        except Exception:
            logger.exception(
                "Failed to auto-generate weekly feedback for plan %s",
                plan.id,
            )


async def _send_daily_task_reminders_job() -> None:
    """每日 08:00 发送今日任务提醒。"""
    from ai_parenting.backend.services.scheduler_service import send_daily_task_reminders

    async with async_session_factory() as session:
        try:
            await send_daily_task_reminders(session)
            await session.commit()
        except Exception:
            await session.rollback()
            logger.exception("Daily task reminders job failed")


async def _send_record_prompts_job() -> None:
    """每日 18:00 发送记录提示。"""
    from ai_parenting.backend.services.scheduler_service import send_record_prompts

    async with async_session_factory() as session:
        try:
            await send_record_prompts(session)
            await session.commit()
        except Exception:
            await session.rollback()
            logger.exception("Record prompts job failed")


def start_scheduler() -> None:
    """启动定时任务调度器。"""
    global _scheduler

    if _scheduler is not None:
        logger.warning("Scheduler already running")
        return

    _scheduler = AsyncIOScheduler(timezone=timezone.utc)

    # 每日 00:01 UTC 推进计划日 (北京时间 08:01)
    _scheduler.add_job(
        _advance_plans_job,
        CronTrigger(hour=16, minute=1, timezone=timezone.utc),  # UTC 16:01 = CST 00:01
        id="advance_plans",
        name="Daily plan advancement",
        replace_existing=True,
    )

    # 每日 00:00 UTC 发送任务提醒 (北京时间 08:00)
    _scheduler.add_job(
        _send_daily_task_reminders_job,
        CronTrigger(hour=0, minute=0, timezone=timezone.utc),  # UTC 00:00 = CST 08:00
        id="daily_task_reminders",
        name="Daily task reminders",
        replace_existing=True,
    )

    # 每日 10:00 UTC 发送记录提示 (北京时间 18:00)
    _scheduler.add_job(
        _send_record_prompts_job,
        CronTrigger(hour=10, minute=0, timezone=timezone.utc),  # UTC 10:00 = CST 18:00
        id="record_prompts",
        name="Record prompts",
        replace_existing=True,
    )

    _scheduler.start()
    logger.info("Scheduler started with %d jobs", len(_scheduler.get_jobs()))


def stop_scheduler() -> None:
    """关闭定时任务调度器。"""
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
        logger.info("Scheduler stopped")
