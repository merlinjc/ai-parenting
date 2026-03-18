"""首页聚合路由。

提供 GET /home/summary 单端点聚合首页全部数据。
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from ai_parenting.backend.auth import get_current_user_id
from ai_parenting.backend.database import get_db
from ai_parenting.backend.schemas import (
    ChildResponse,
    DayTaskResponse,
    HomeSummaryResponse,
    PlanResponse,
    RecordResponse,
)
from ai_parenting.backend.services import home_service
from ai_parenting.backend.services.child_service import get_child

router = APIRouter(prefix="/home", tags=["home"])


@router.get("/summary", response_model=HomeSummaryResponse)
async def get_home_summary(
    child_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    """获取首页聚合数据。"""
    # P0-4: 校验 child_id 所有权
    child = await get_child(db, child_id)
    if child is None:
        raise HTTPException(status_code=404, detail="Child not found")
    if child.user_id != user_id:
        raise HTTPException(status_code=403, detail="无权访问此儿童数据")
    data = await home_service.get_home_summary(db, user_id, child_id)

    return HomeSummaryResponse(
        child=ChildResponse.model_validate(data["child"]) if data["child"] else None,
        active_plan=PlanResponse.model_validate(data["active_plan"]) if data["active_plan"] else None,
        today_task=DayTaskResponse.model_validate(data["today_task"]) if data["today_task"] else None,
        recent_records=[RecordResponse.model_validate(r) for r in data["recent_records"]],
        unread_count=data["unread_count"],
        weekly_feedback_status=data["weekly_feedback_status"],
        weekly_feedback_id=data["weekly_feedback_id"],
        greeting=data["greeting"],
        streak_days=data["streak_days"],
        week_day_statuses=data["week_day_statuses"],
        plan_generating=data.get("plan_generating", False),
    )
