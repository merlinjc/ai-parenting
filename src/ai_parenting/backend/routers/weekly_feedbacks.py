"""周反馈路由。

提供周反馈生成触发（返回 202）、查询详情、决策回写端点。
AI 生成通过 FastAPI BackgroundTasks 异步执行。
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from ai_parenting.backend.database import get_db, async_session_factory
from ai_parenting.backend.deps import get_orchestrator
from ai_parenting.backend.schemas import (
    WeeklyFeedbackCreateRequest,
    WeeklyFeedbackDecisionRequest,
    WeeklyFeedbackResponse,
)
from ai_parenting.backend.services import weekly_feedback_service
from ai_parenting.orchestrator import Orchestrator

router = APIRouter(prefix="/weekly-feedbacks", tags=["weekly-feedbacks"])


async def _background_generate(
    orchestrator: Orchestrator,
    feedback_id: uuid.UUID,
) -> None:
    """后台任务：执行周反馈 AI 生成。

    使用独立的 DB session 以避免与请求 session 冲突。
    """
    async with async_session_factory() as db:
        try:
            await weekly_feedback_service.generate_feedback_background(
                db, orchestrator, feedback_id,
            )
            await db.commit()
        except Exception:
            await db.rollback()


@router.post("", response_model=WeeklyFeedbackResponse, status_code=202)
async def create_weekly_feedback(
    body: WeeklyFeedbackCreateRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    orchestrator: Orchestrator = Depends(get_orchestrator),
):
    """触发周反馈生成（异步）。

    立即返回 202 和 generating 状态的记录，AI 生成在后台执行。
    """
    try:
        feedback = await weekly_feedback_service.create_weekly_feedback(
            db, body.plan_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    # 仅当新创建（generating 状态）时启动后台任务
    if feedback.status == "generating":
        background_tasks.add_task(
            _background_generate, orchestrator, feedback.id,
        )

    return WeeklyFeedbackResponse.model_validate(feedback)


@router.get("/{feedback_id}", response_model=WeeklyFeedbackResponse)
async def get_weekly_feedback(
    feedback_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """查询周反馈详情。"""
    feedback = await weekly_feedback_service.get_feedback(db, feedback_id)
    if not feedback:
        raise HTTPException(status_code=404, detail="周反馈不存在")
    return WeeklyFeedbackResponse.model_validate(feedback)


@router.post("/{feedback_id}/viewed", response_model=WeeklyFeedbackResponse)
async def mark_feedback_viewed(
    feedback_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """标记周反馈为已查看。"""
    feedback = await weekly_feedback_service.mark_viewed(db, feedback_id)
    if not feedback:
        raise HTTPException(status_code=404, detail="周反馈不存在")
    return WeeklyFeedbackResponse.model_validate(feedback)


@router.post("/{feedback_id}/decision", response_model=WeeklyFeedbackResponse)
async def submit_feedback_decision(
    feedback_id: uuid.UUID,
    body: WeeklyFeedbackDecisionRequest,
    db: AsyncSession = Depends(get_db),
):
    """提交周反馈决策。"""
    try:
        feedback = await weekly_feedback_service.submit_decision(
            db, feedback_id, body.decision,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    if not feedback:
        raise HTTPException(status_code=404, detail="周反馈不存在")
    return WeeklyFeedbackResponse.model_validate(feedback)
