"""定时任务调度器。

使用 APScheduler 管理定时任务：
- 每日零点推进计划 current_day + 自动触发周反馈
- SmartPushEngine 每小时扫描：时区感知推送（smart 模式）
- Legacy 模式：固定 UTC 时间推送（兼容旧逻辑）

通过 config.push_engine_mode 切换：
- "smart"：SmartPushEngine 驱动所有推送（推荐）
- "legacy"：保留原有固定 Cron 任务（向后兼容）
"""

from __future__ import annotations

import logging
from datetime import timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from ai_parenting.backend.database import async_session_factory

logger = logging.getLogger(__name__)

_scheduler: AsyncIOScheduler | None = None


# ---------------------------------------------------------------------------
# 通用任务：计划推进（不受 push_engine_mode 影响）
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Smart 模式：SmartPushEngine 驱动
# ---------------------------------------------------------------------------


async def _smart_push_scan_job() -> None:
    """SmartPushEngine 每小时扫描任务。

    时区感知：按每个用户的本地时间判断是否在规则触发窗口内，
    无需为不同时区设置多个 Cron 任务。
    使用依赖注入的 SmartPushEngine 单例（已注入 ChannelRouter）。
    """
    from ai_parenting.backend.deps import get_push_engine

    engine = get_push_engine()
    async with async_session_factory() as session:
        try:
            stats = await engine.scan_and_push(session)
            logger.info("Smart push scan: %s", stats)
        except Exception:
            await session.rollback()
            logger.exception("Smart push scan job failed")


# ---------------------------------------------------------------------------
# Legacy 模式：固定 UTC Cron 任务（向后兼容）
# ---------------------------------------------------------------------------


async def _send_daily_task_reminders_job() -> None:
    """[Legacy] 每日 08:00 CST 发送今日任务提醒。"""
    from ai_parenting.backend.services.scheduler_service import send_daily_task_reminders

    async with async_session_factory() as session:
        try:
            await send_daily_task_reminders(session)
            await session.commit()
        except Exception:
            await session.rollback()
            logger.exception("Daily task reminders job failed")


async def _send_record_prompts_job() -> None:
    """[Legacy] 每日 18:00 CST 发送记录提示。"""
    from ai_parenting.backend.services.scheduler_service import send_record_prompts

    async with async_session_factory() as session:
        try:
            await send_record_prompts(session)
            await session.commit()
        except Exception:
            await session.rollback()
            logger.exception("Record prompts job failed")


# ---------------------------------------------------------------------------
# 调度器启动/停止
# ---------------------------------------------------------------------------


def _get_push_engine_mode() -> str:
    """获取推送引擎模式配置。"""
    from ai_parenting.backend.config import settings

    return getattr(settings, "push_engine_mode", "legacy")


def start_scheduler() -> None:
    """启动定时任务调度器。

    根据 push_engine_mode 选择推送策略：
    - smart：每小时运行 SmartPushEngine 扫描
    - legacy：固定 UTC Cron 任务（向后兼容）
    """
    global _scheduler

    if _scheduler is not None:
        logger.warning("Scheduler already running")
        return

    mode = _get_push_engine_mode()
    _scheduler = AsyncIOScheduler(timezone=timezone.utc)

    # ---- 通用任务（不受模式影响） ----

    # 每日 00:01 UTC 推进计划日 (北京时间 08:01)
    _scheduler.add_job(
        _advance_plans_job,
        CronTrigger(hour=16, minute=1, timezone=timezone.utc),  # UTC 16:01 = CST 00:01
        id="advance_plans",
        name="Daily plan advancement",
        replace_existing=True,
    )

    # ---- 推送模式分支 ----

    if mode == "smart":
        # SmartPushEngine：每小时整点扫描
        _scheduler.add_job(
            _smart_push_scan_job,
            IntervalTrigger(hours=1),
            id="smart_push_scan",
            name="Smart push engine hourly scan",
            replace_existing=True,
        )
        logger.info("Push engine mode: SMART (hourly scan)")

    else:
        # Legacy 模式：固定 UTC Cron
        _scheduler.add_job(
            _send_daily_task_reminders_job,
            CronTrigger(hour=0, minute=0, timezone=timezone.utc),  # UTC 00:00 = CST 08:00
            id="daily_task_reminders",
            name="[Legacy] Daily task reminders",
            replace_existing=True,
        )
        _scheduler.add_job(
            _send_record_prompts_job,
            CronTrigger(hour=10, minute=0, timezone=timezone.utc),  # UTC 10:00 = CST 18:00
            id="record_prompts",
            name="[Legacy] Record prompts",
            replace_existing=True,
        )
        logger.info("Push engine mode: LEGACY (fixed UTC cron)")

    _scheduler.start()
    logger.info("Scheduler started with %d jobs", len(_scheduler.get_jobs()))


def stop_scheduler() -> None:
    """关闭定时任务调度器。"""
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
        logger.info("Scheduler stopped")
