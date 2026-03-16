"""AI 会话服务。

管理 AI 会话生命周期，集成 Orchestrator 编排层。
支持即时求助和微计划生成两种核心场景。
包含风险升级后处理和审计日志。
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ai_parenting.backend.audit import log_ai_session, log_risk_escalation
from ai_parenting.backend.models import AISession, Child, Plan
from ai_parenting.backend.services import child_service, message_service, plan_service, record_service
from ai_parenting.models.enums import SessionStatus, SessionType
from ai_parenting.models.schemas import ContextSnapshot
from ai_parenting.orchestrator import Orchestrator


async def _check_risk_escalation(
    db: AsyncSession,
    child: Child,
    session: AISession,
    result_dict: dict | None,
) -> None:
    """检查 AI 结果中的风险升级信号并执行升级。

    如果 suggest_consult_prep=True 且 child.risk_level 不是 consult，
    自动升级 risk_level 并创建 risk_alert 消息。
    """
    if result_dict is None:
        return

    suggest_consult = result_dict.get("suggest_consult_prep", False)
    if not suggest_consult:
        return

    if child.risk_level == "consult":
        return  # 已经是 consult 级别，不需要升级

    previous_level = child.risk_level
    child.risk_level = "consult"

    # 创建风险提醒消息
    message = await message_service.create_message(
        db,
        user_id=child.user_id,
        child_id=child.id,
        message_type="risk_alert",
        target_params={"child_id": str(child.id)},
    )

    # 审计日志
    log_risk_escalation(
        child_id=child.id,
        session_id=session.id,
        previous_level=previous_level,
        new_level="consult",
        trigger="suggest_consult_prep",
        message_id=message.id,
    )


async def _build_context_snapshot(
    db: AsyncSession, child: Child, active_plan: Plan | None
) -> ContextSnapshot:
    """从数据库构建 AI 编排层所需的 ContextSnapshot。"""
    recent_records = await record_service.get_recent_records(db, child.id, count=3)

    return ContextSnapshot(
        child_age_months=child.age_months,
        child_stage=child.stage,
        child_focus_themes=child.focus_themes or [],
        child_risk_level=child.risk_level,
        active_plan_id=str(active_plan.id) if active_plan else None,
        active_plan_day=active_plan.current_day if active_plan else None,
        recent_record_ids=[str(r.id) for r in recent_records],
        recent_record_keywords=[
            t for r in recent_records for t in (r.tags or [])
        ][:10],
    )


async def create_instant_help_session(
    db: AsyncSession,
    orchestrator: Orchestrator,
    child_id: uuid.UUID,
    scenario: str | None = None,
    input_text: str | None = None,
    plan_id: uuid.UUID | None = None,
) -> AISession:
    """创建即时求助 AI 会话并执行 AI 调用。

    流程：
    1. 获取儿童和计划上下文
    2. 构建 ContextSnapshot
    3. 创建 pending 状态的 AISession
    4. 调用 Orchestrator
    5. 更新 AISession 为 completed/failed/degraded
    """
    child = await child_service.get_child(db, child_id)
    if child is None:
        raise ValueError(f"Child {child_id} not found")

    active_plan = None
    if plan_id:
        active_plan = await plan_service.get_plan(db, plan_id)
    else:
        active_plan = await plan_service.get_active_plan(db, child_id)

    context = await _build_context_snapshot(db, child, active_plan)

    # 创建 AISession（pending）
    session = AISession(
        child_id=child_id,
        session_type=SessionType.INSTANT_HELP.value,
        status=SessionStatus.PENDING.value,
        input_scenario=scenario,
        input_text=input_text,
        context_snapshot=context.model_dump(),
    )
    db.add(session)
    await db.flush()

    # 调用 Orchestrator
    session.status = SessionStatus.PROCESSING.value
    await db.flush()

    try:
        result = await orchestrator.orchestrate(
            session_type=SessionType.INSTANT_HELP,
            context=context,
            user_scenario=scenario or "",
            user_input_text=input_text or "",
            child_nickname=child.nickname,
            active_plan_title=active_plan.title if active_plan else "",
            recent_records_summary=", ".join(context.recent_record_keywords[:5]),
        )

        session.status = result.status.value
        session.result = result.result.model_dump() if result.result else None
        session.model_provider = result.metadata.model_provider
        session.model_version = result.metadata.model_version
        session.prompt_template_id = result.metadata.prompt_template_version
        session.latency_ms = result.metadata.latency_ms
        session.completed_at = datetime.now(timezone.utc)

        if result.status == SessionStatus.DEGRADED and result.result:
            session.degraded_result = result.result.model_dump()

        # 风险升级检查（即时求助结果中的 suggest_consult_prep）
        if result.result:
            await _check_risk_escalation(db, child, session, result.result.model_dump())

        # 审计日志
        log_ai_session(
            session_id=session.id,
            session_type=SessionType.INSTANT_HELP.value,
            child_id=child_id,
            status=session.status,
            latency_ms=session.latency_ms,
            is_degraded=(result.status == SessionStatus.DEGRADED),
            model_provider=session.model_provider,
        )

    except Exception as exc:
        session.status = SessionStatus.FAILED.value
        session.error_info = str(exc)
        session.completed_at = datetime.now(timezone.utc)

    await db.flush()
    await db.refresh(session)
    return session


async def create_plan_generation_session(
    db: AsyncSession,
    orchestrator: Orchestrator,
    child_id: uuid.UUID,
) -> AISession:
    """创建微计划生成 AI 会话并执行 AI 调用。

    成功后自动调用 plan_service.create_plan_from_ai_result 创建计划。
    """
    child = await child_service.get_child(db, child_id)
    if child is None:
        raise ValueError(f"Child {child_id} not found")

    active_plan = await plan_service.get_active_plan(db, child_id)
    context = await _build_context_snapshot(db, child, active_plan)

    # 获取最近记录摘要
    recent_records = await record_service.get_recent_records(db, child_id, count=5)
    records_summary = "; ".join(
        r.content[:50] if r.content else ", ".join(r.tags or [])
        for r in recent_records
    )

    session = AISession(
        child_id=child_id,
        session_type=SessionType.PLAN_GENERATION.value,
        status=SessionStatus.PENDING.value,
        context_snapshot=context.model_dump(),
    )
    db.add(session)
    await db.flush()

    session.status = SessionStatus.PROCESSING.value
    await db.flush()

    try:
        result = await orchestrator.orchestrate(
            session_type=SessionType.PLAN_GENERATION,
            context=context,
            child_nickname=child.nickname,
            recent_records_summary=records_summary,
        )

        session.status = result.status.value
        session.result = result.result.model_dump() if result.result else None
        session.model_provider = result.metadata.model_provider
        session.model_version = result.metadata.model_version
        session.prompt_template_id = result.metadata.prompt_template_version
        session.latency_ms = result.metadata.latency_ms
        session.completed_at = datetime.now(timezone.utc)

        # 成功时自动创建计划
        if result.status in (SessionStatus.COMPLETED, SessionStatus.DEGRADED):
            if result.result:
                ai_result_dict = result.result.model_dump()
                await plan_service.create_plan_from_ai_result(
                    db, child, session, ai_result_dict
                )

        # 审计日志
        log_ai_session(
            session_id=session.id,
            session_type=SessionType.PLAN_GENERATION.value,
            child_id=child_id,
            status=session.status,
            latency_ms=session.latency_ms,
            is_degraded=(result.status == SessionStatus.DEGRADED),
            model_provider=session.model_provider,
        )

    except Exception as exc:
        session.status = SessionStatus.FAILED.value
        session.error_info = str(exc)
        session.completed_at = datetime.now(timezone.utc)

    await db.flush()
    await db.refresh(session)
    return session


async def get_session(db: AsyncSession, session_id: uuid.UUID) -> AISession | None:
    """按 ID 获取 AI 会话。"""
    result = await db.execute(
        select(AISession).where(AISession.id == session_id)
    )
    return result.scalar_one_or_none()
