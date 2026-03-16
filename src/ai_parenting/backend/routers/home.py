"""首页聚合路由。

提供 GET /home/summary 单端点聚合首页全部数据。
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession

from ai_parenting.backend.database import get_db
from ai_parenting.backend.schemas import (
    ChildResponse,
    DayTaskResponse,
    HomeSummaryResponse,
    PlanResponse,
    RecordResponse,
)
from ai_parenting.backend.services import home_service

router = APIRouter(prefix="/home", tags=["home"])

_DEFAULT_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


def _get_user_id(x_user_id: str | None = Header(None, alias="X-User-Id")) -> uuid.UUID:
    if x_user_id:
        return uuid.UUID(x_user_id)
    return _DEFAULT_USER_ID


@router.get("/summary", response_model=HomeSummaryResponse)
async def get_home_summary(
    child_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(_get_user_id),
):
    """获取首页聚合数据。"""
    data = await home_service.get_home_summary(db, user_id, child_id)

    return HomeSummaryResponse(
        child=ChildResponse.model_validate(data["child"]) if data["child"] else None,
        active_plan=PlanResponse.model_validate(data["active_plan"]) if data["active_plan"] else None,
        today_task=DayTaskResponse.model_validate(data["today_task"]) if data["today_task"] else None,
        recent_records=[RecordResponse.model_validate(r) for r in data["recent_records"]],
        unread_count=data["unread_count"],
        weekly_feedback_status=data["weekly_feedback_status"],
        weekly_feedback_id=data["weekly_feedback_id"],
    )
