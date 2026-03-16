"""首页聚合服务。

实现 GET /home/summary 所需的数据聚合，
在单次 DB session 内完成 child + plan + today_task + records + unread_count 查询。
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from ai_parenting.backend.services import (
    child_service,
    message_service,
    plan_service,
    record_service,
    weekly_feedback_service,
)


async def get_home_summary(
    db: AsyncSession,
    user_id: uuid.UUID,
    child_id: uuid.UUID,
) -> dict[str, Any]:
    """聚合首页所需的全部数据。

    返回字典包含：child, active_plan, today_task,
    recent_records, unread_count, weekly_feedback_status, weekly_feedback_id。
    """
    child = await child_service.get_child(db, child_id)

    active_plan = None
    today_task = None
    weekly_feedback_status = None
    weekly_feedback_id = None

    if child:
        active_plan = await plan_service.get_active_plan(db, child_id)
        if active_plan:
            today_task = await plan_service.get_today_task(db, active_plan)
            # 查询周反馈状态
            feedback = await weekly_feedback_service.get_feedback_for_plan(
                db, active_plan.id,
            )
            if feedback:
                weekly_feedback_status = feedback.status
                weekly_feedback_id = feedback.id

    recent_records = await record_service.get_recent_records(db, child_id, count=5)
    unread_count = await message_service.get_unread_count(db, user_id)

    return {
        "child": child,
        "active_plan": active_plan,
        "today_task": today_task,
        "recent_records": recent_records,
        "unread_count": unread_count,
        "weekly_feedback_status": weekly_feedback_status,
        "weekly_feedback_id": weekly_feedback_id,
    }
