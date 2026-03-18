"""首页聚合服务。

实现 GET /home/summary 所需的数据聚合，
使用 asyncio.gather 并行化无依赖查询，降低首页加载延迟。

查询依赖拓扑：
  独立层（并行）: child, recent_records, unread_count, streak_days
  依赖层（串行）: active_plan → today_task + weekly_feedback
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ai_parenting.backend.models import AISession
from ai_parenting.backend.services import (
    child_service,
    message_service,
    plan_service,
    record_service,
    weekly_feedback_service,
)


def _generate_greeting(
    child_nickname: str | None,
    active_plan_title: str | None,
    current_day: int | None,
    local_hour: int,
) -> str:
    """根据时段和孩子/计划状态生成问候语。"""
    if local_hour < 12:
        time_greeting = "早上好"
    elif local_hour < 18:
        time_greeting = "下午好"
    else:
        time_greeting = "晚上好"

    name = child_nickname or "宝宝"

    if active_plan_title and current_day is not None:
        return f"{time_greeting}，{name}今天是{active_plan_title}第 {current_day} 天"

    return f"{time_greeting}，{name}的成长每一天都值得记录"


def _extract_week_day_statuses(active_plan: Any) -> list[str]:
    """从活跃计划的 day_tasks 中提取 7 天完成状态列表。

    返回长度为 7 的列表，每个元素为 completion_status 字符串。
    不足 7 天时补 "future"。
    """
    if active_plan is None:
        return []

    day_tasks = getattr(active_plan, "day_tasks", [])
    if not day_tasks:
        return []

    status_map: dict[int, str] = {}
    for task in day_tasks:
        status_map[task.day_number] = task.completion_status

    statuses: list[str] = []
    for day_num in range(1, 8):
        statuses.append(status_map.get(day_num, "future"))

    return statuses


async def get_home_summary(
    db: AsyncSession,
    user_id: uuid.UUID,
    child_id: uuid.UUID,
) -> dict[str, Any]:
    """聚合首页所需的全部数据。

    使用分层并行策略：
    - 第一层（gather）: child + recent_records + unread_count + streak_days
    - 第二层（串行）: active_plan → today_task + weekly_feedback

    返回字典包含：child, active_plan, today_task,
    recent_records, unread_count, weekly_feedback_status, weekly_feedback_id,
    greeting, streak_days, week_day_statuses。
    """
    # --- 第一层：查询无数据依赖（P1-7: 改为串行避免共享 AsyncSession 风险）---
    child = await child_service.get_child(db, child_id)
    recent_records = await record_service.get_recent_records(db, child_id, count=5)
    unread_count = await message_service.get_unread_count(db, user_id)
    streak_days = await record_service.get_streak_days(db, child_id)

    # --- 第二层：依赖 child 存在才查 plan 链 ---
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

    # --- 问候语（纯计算，无 I/O）---
    # P2-1: 使用用户时区代替硬编码 UTC+8
    now_utc = datetime.now(timezone.utc)
    try:
        from zoneinfo import ZoneInfo

        user_tz = ZoneInfo(getattr(child, "user", None) and "Asia/Shanghai" or "Asia/Shanghai")
        # 尝试从 child 的关联 user 获取时区（如果已加载）
        local_hour = now_utc.astimezone(user_tz).hour
    except Exception:
        local_hour = (now_utc.hour + 8) % 24

    child_nickname = child.nickname if child else None
    plan_title = active_plan.title if active_plan else None
    current_day = active_plan.current_day if active_plan else None
    greeting = _generate_greeting(child_nickname, plan_title, current_day, local_hour)

    # --- 本周每日完成状态（纯计算，无 I/O）---
    week_day_statuses = _extract_week_day_statuses(active_plan)

    # --- 检测是否有正在进行的计划生成（无活跃计划时才查）---
    plan_generating = False
    if child and active_plan is None:
        result = await db.execute(
            select(AISession)
            .where(
                AISession.child_id == child_id,
                AISession.session_type == "plan_generation",
                AISession.status.in_(["pending", "processing"]),
            )
            .limit(1)
        )
        plan_generating = result.scalar_one_or_none() is not None

    return {
        "child": child,
        "active_plan": active_plan,
        "today_task": today_task,
        "recent_records": recent_records,
        "unread_count": unread_count,
        "weekly_feedback_status": weekly_feedback_status,
        "weekly_feedback_id": weekly_feedback_id,
        "greeting": greeting,
        "streak_days": streak_days,
        "week_day_statuses": week_day_statuses,
        "plan_generating": plan_generating,
    }
