"""周反馈服务。

实现周反馈的完整生命周期：
- 创建：接收 plan_id，创建 generating 状态记录，后台异步生成
- 后台生成：聚合计划完成率+本周记录，调用 AI Orchestrator，更新结果
- 查询：按 ID 获取周反馈详情
- 决策回写：家长选择下周方向，同步更新 Plan.next_week_direction
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ai_parenting.backend.audit import log_ai_session
from ai_parenting.backend.models import (
    AISession,
    Child,
    Plan,
    WeeklyFeedback,
)
from ai_parenting.backend.services import (
    child_service,
    message_service,
    plan_service,
    record_service,
)
from ai_parenting.models.enums import (
    FeedbackStatus,
    SessionStatus,
    SessionType,
)
from ai_parenting.models.schemas import ContextSnapshot
from ai_parenting.orchestrator import Orchestrator


async def get_feedback(
    db: AsyncSession,
    feedback_id: uuid.UUID,
) -> WeeklyFeedback | None:
    """按 ID 获取周反馈。"""
    result = await db.execute(
        select(WeeklyFeedback).where(WeeklyFeedback.id == feedback_id)
    )
    return result.scalar_one_or_none()


async def get_feedback_for_plan(
    db: AsyncSession,
    plan_id: uuid.UUID,
) -> WeeklyFeedback | None:
    """获取指定计划的周反馈（排除 failed 状态）。"""
    result = await db.execute(
        select(WeeklyFeedback)
        .where(
            WeeklyFeedback.plan_id == plan_id,
            WeeklyFeedback.status != FeedbackStatus.FAILED.value,
        )
        .order_by(WeeklyFeedback.created_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def create_weekly_feedback(
    db: AsyncSession,
    plan_id: uuid.UUID,
) -> WeeklyFeedback:
    """创建周反馈记录（generating 状态）。

    幂等检查：如果已存在非 failed 的周反馈，直接返回。
    """
    # 幂等检查
    existing = await get_feedback_for_plan(db, plan_id)
    if existing is not None:
        return existing

    # 获取计划和儿童
    plan = await plan_service.get_plan(db, plan_id)
    if plan is None:
        raise ValueError(f"Plan {plan_id} not found")

    feedback = WeeklyFeedback(
        plan_id=plan_id,
        child_id=plan.child_id,
        status=FeedbackStatus.GENERATING.value,
    )
    db.add(feedback)
    await db.flush()
    return feedback


async def generate_feedback_background(
    db: AsyncSession,
    orchestrator: Orchestrator,
    feedback_id: uuid.UUID,
) -> None:
    """后台执行周反馈 AI 生成。

    流程：
    1. 聚合 Plan 完成率 + 本周 Records
    2. 构建 ContextSnapshot
    3. 调用 Orchestrator(WEEKLY_FEEDBACK)
    4. 更新 WeeklyFeedback(ready/failed) + 写入 AI 结果
    5. 创建消息通知
    """
    feedback = await get_feedback(db, feedback_id)
    if feedback is None:
        return

    # 防止重复执行
    if feedback.status != FeedbackStatus.GENERATING.value:
        return

    plan = await plan_service.get_plan(db, feedback.plan_id)
    if plan is None:
        feedback.status = FeedbackStatus.FAILED.value
        feedback.error_info = "Plan not found"
        await db.flush()
        return

    child = await child_service.get_child(db, plan.child_id)
    if child is None:
        feedback.status = FeedbackStatus.FAILED.value
        feedback.error_info = "Child not found"
        await db.flush()
        return

    # 聚合数据
    plan_start = datetime(
        plan.start_date.year,
        plan.start_date.month,
        plan.start_date.day,
        tzinfo=timezone.utc,
    )
    weekly_records = await record_service.get_weekly_records(db, child.id, plan_start)
    record_count = await record_service.count_weekly_records(db, child.id, plan_start)
    recent_records = await record_service.get_recent_records(db, child.id, count=5)

    # 构建 day_tasks_summary
    day_tasks_summary = "; ".join(
        f"Day{t.day_number}: {t.main_exercise_title} ({t.completion_status})"
        for t in plan.day_tasks
    )

    # 构建 weekly_records_detail
    weekly_records_detail = "; ".join(
        r.content[:50] if r.content else ", ".join(r.tags or [])
        for r in weekly_records[:10]
    )

    # 构建 ContextSnapshot
    active_plan = await plan_service.get_active_plan(db, child.id)
    context = ContextSnapshot(
        child_age_months=child.age_months,
        child_stage=child.stage,
        child_focus_themes=child.focus_themes or [],
        child_risk_level=child.risk_level,
        active_plan_id=str(plan.id),
        active_plan_day=plan.current_day,
        recent_record_ids=[str(r.id) for r in recent_records],
        recent_record_keywords=[
            t for r in recent_records for t in (r.tags or [])
        ][:10],
    )

    # 创建 AISession
    session = AISession(
        child_id=child.id,
        session_type=SessionType.WEEKLY_FEEDBACK.value,
        status=SessionStatus.PENDING.value,
        context_snapshot=context.model_dump(),
    )
    db.add(session)
    await db.flush()

    session.status = SessionStatus.PROCESSING.value
    await db.flush()

    try:
        result = await orchestrator.orchestrate(
            session_type=SessionType.WEEKLY_FEEDBACK,
            context=context,
            child_nickname=child.nickname,
            active_plan_title=plan.title,
            active_plan_focus_theme=plan.focus_theme,
            plan_completion_rate=f"{plan.completion_rate * 100:.0f}%",
            record_count_this_week=record_count,
            day_tasks_summary=day_tasks_summary,
            weekly_records_detail=weekly_records_detail,
            active_plan_id=str(plan.id),
        )

        session.status = result.status.value
        session.result = result.result.model_dump() if result.result else None
        session.model_provider = result.metadata.model_provider
        session.model_version = result.metadata.model_version
        session.prompt_template_id = result.metadata.prompt_template_version
        session.latency_ms = result.metadata.latency_ms
        session.completed_at = datetime.now(timezone.utc)

        # 更新周反馈
        feedback.ai_generation_id = session.id
        feedback.record_count_this_week = record_count
        feedback.completion_rate_this_week = plan.completion_rate

        if result.result:
            result_dict = result.result.model_dump()
            feedback.positive_changes = result_dict.get("positive_changes")
            feedback.opportunities = result_dict.get("next_week_opportunities")
            feedback.summary_text = result_dict.get("summary")
            feedback.decision_options = result_dict.get("decision_options")
            feedback.conservative_path_note = result_dict.get("conservative_path_note")
            feedback.status = FeedbackStatus.READY.value
        else:
            feedback.status = FeedbackStatus.FAILED.value
            feedback.error_info = "AI returned no result"

        # 审计日志
        log_ai_session(
            session_id=session.id,
            session_type=SessionType.WEEKLY_FEEDBACK.value,
            child_id=child.id,
            status=session.status,
            latency_ms=session.latency_ms,
            is_degraded=(result.status == SessionStatus.DEGRADED),
            model_provider=session.model_provider,
        )

    except Exception as exc:
        session.status = SessionStatus.FAILED.value
        session.error_info = str(exc)
        session.completed_at = datetime.now(timezone.utc)

        feedback.status = FeedbackStatus.FAILED.value
        feedback.error_info = str(exc)

    await db.flush()

    # 如果生成成功，创建通知消息
    if feedback.status == FeedbackStatus.READY.value:
        await message_service.create_message(
            db,
            user_id=child.user_id,
            child_id=child.id,
            message_type="weekly_feedback_ready",
            target_params={"feedback_id": str(feedback.id)},
        )
        await db.flush()


async def submit_decision(
    db: AsyncSession,
    feedback_id: uuid.UUID,
    decision: str,
) -> WeeklyFeedback | None:
    """提交周反馈决策，联动更新 Plan.next_week_direction。"""
    feedback = await get_feedback(db, feedback_id)
    if feedback is None:
        return None

    if feedback.status not in (
        FeedbackStatus.READY.value,
        FeedbackStatus.VIEWED.value,
    ):
        raise ValueError(
            f"Cannot submit decision for feedback in status: {feedback.status}"
        )

    feedback.selected_decision = decision
    feedback.status = FeedbackStatus.DECIDED.value
    feedback.decided_at = datetime.now(timezone.utc)

    # 联动更新 Plan.next_week_direction
    plan = await plan_service.get_plan(db, feedback.plan_id)
    if plan is not None:
        plan.next_week_direction = decision

    await db.flush()
    return feedback


async def mark_viewed(
    db: AsyncSession,
    feedback_id: uuid.UUID,
) -> WeeklyFeedback | None:
    """标记周反馈为已查看。"""
    feedback = await get_feedback(db, feedback_id)
    if feedback is None:
        return None

    if feedback.status == FeedbackStatus.READY.value:
        feedback.status = FeedbackStatus.VIEWED.value
        feedback.viewed_at = datetime.now(timezone.utc)
        await db.flush()

    return feedback
