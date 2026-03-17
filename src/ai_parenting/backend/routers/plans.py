"""微计划与日任务路由。

提供活跃计划查询、计划创建（触发 AI 生成）和日任务完成状态更新。
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from ai_parenting.backend.auth import get_current_user_id
from ai_parenting.backend.database import get_db
from ai_parenting.backend.deps import get_orchestrator
from ai_parenting.backend.schemas import (
    DayTaskCompletionUpdate,
    DayTaskResponse,
    PlanCreateRequest,
    PlanFocusNoteUpdate,
    PlanListResponse,
    PlanResponse,
    PlanWithFeedbackStatus,
)
from ai_parenting.backend.services import plan_service
from ai_parenting.backend.services import weekly_feedback_service
from ai_parenting.backend.services.ai_session_service import (
    create_plan_generation_session,
)
from ai_parenting.orchestrator import Orchestrator

router = APIRouter(prefix="/plans", tags=["plans"])


@router.get("/active", response_model=PlanWithFeedbackStatus)
async def get_active_plan(
    child_id: uuid.UUID,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> PlanWithFeedbackStatus:
    """获取儿童当前活跃计划（含 7 个日任务和周反馈状态）。"""
    plan = await plan_service.get_active_plan(db, child_id)
    if plan is None:
        raise HTTPException(status_code=404, detail="No active plan found")

    # 查询真实的周反馈状态
    feedback = await weekly_feedback_service.get_feedback_for_plan(db, plan.id)
    feedback_status = feedback.status if feedback else None

    return PlanWithFeedbackStatus(
        plan=PlanResponse.model_validate(plan),
        weekly_feedback_status=feedback_status,
    )


@router.get("", response_model=PlanListResponse)
async def list_plans(
    child_id: uuid.UUID,
    limit: int = 20,
    offset: int = 0,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> PlanListResponse:
    """获取儿童的历次计划列表（按创建时间降序，含分页）。"""
    if limit < 1 or limit > 100:
        raise HTTPException(status_code=400, detail="limit must be 1-100")
    if offset < 0:
        raise HTTPException(status_code=400, detail="offset must be >= 0")

    plans, total = await plan_service.list_plans(db, child_id, limit=limit, offset=offset)
    plan_responses = [PlanResponse.model_validate(p) for p in plans]
    return PlanListResponse(
        plans=plan_responses,
        has_more=(offset + limit) < total,
        total=total,
    )


@router.get("/{plan_id}", response_model=PlanResponse)
async def get_plan(
    plan_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> PlanResponse:
    """获取计划详情。"""
    plan = await plan_service.get_plan(db, plan_id)
    if plan is None:
        raise HTTPException(status_code=404, detail="Plan not found")
    return PlanResponse.model_validate(plan)


@router.post("", response_model=PlanResponse, status_code=201)
async def create_plan(
    body: PlanCreateRequest,
    db: AsyncSession = Depends(get_db),
    orchestrator: Orchestrator = Depends(get_orchestrator),
) -> PlanResponse:
    """创建微计划（触发 AI 生成）。

    流程：调用 AI 生成 → 创建 Plan + 7 DayTask → 返回。
    """
    session = await create_plan_generation_session(
        db, orchestrator, body.child_id
    )

    if session.status in ("failed",):
        raise HTTPException(
            status_code=500,
            detail=f"AI generation failed: {session.error_info}",
        )

    # 获取新创建的活跃计划
    plan = await plan_service.get_active_plan(db, body.child_id)
    if plan is None:
        raise HTTPException(status_code=500, detail="Plan creation failed")
    return PlanResponse.model_validate(plan)


@router.post(
    "/{plan_id}/days/{day_number}/completion",
    response_model=DayTaskResponse,
)
async def update_day_completion(
    plan_id: uuid.UUID,
    day_number: int,
    body: DayTaskCompletionUpdate,
    db: AsyncSession = Depends(get_db),
) -> DayTaskResponse:
    """更新日任务完成状态。"""
    if day_number < 1 or day_number > 7:
        raise HTTPException(status_code=400, detail="day_number must be 1-7")

    task, plan = await plan_service.update_day_task_completion(
        db, plan_id, day_number, body.completion_status
    )
    if task is None:
        raise HTTPException(status_code=404, detail="DayTask not found")
    return DayTaskResponse.model_validate(task)


@router.patch("/{plan_id}/focus-note", response_model=PlanResponse)
async def append_focus_note(
    plan_id: uuid.UUID,
    body: PlanFocusNoteUpdate,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> PlanResponse:
    """追加关注内容到计划的 next_week_context（「加入本周关注」功能）。"""
    plan = await plan_service.append_focus_note(db, plan_id, body.note)
    if plan is None:
        raise HTTPException(status_code=404, detail="Plan not found")
    return PlanResponse.model_validate(plan)
