"""微计划与日任务服务。

实现计划创建（含 AI 生成）、日任务管理、完成状态回写和日推进。
"""

from __future__ import annotations

import logging
import uuid
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ai_parenting.backend.models import AISession, Child, DayTask, Plan
from ai_parenting.models.enums import (
    CompletionStatus,
    SessionStatus,
    SessionType,
)

logger = logging.getLogger(__name__)


async def get_active_plan(db: AsyncSession, child_id: uuid.UUID) -> Plan | None:
    """获取儿童当前活跃计划（含 day_tasks）。"""
    result = await db.execute(
        select(Plan)
        .where(Plan.child_id == child_id, Plan.status == "active")
        .order_by(Plan.created_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def get_plan(db: AsyncSession, plan_id: uuid.UUID) -> Plan | None:
    """按 ID 获取计划。"""
    result = await db.execute(select(Plan).where(Plan.id == plan_id))
    return result.scalar_one_or_none()


async def create_plan_from_ai_result(
    db: AsyncSession,
    child: Child,
    ai_session: AISession,
    ai_result: dict,
) -> Plan:
    """根据 AI 生成结果创建计划和 7 个日任务。

    ai_result 应为 PlanGenerationResult 的字典形式。
    """
    # 1. 将已有 active 计划标记为 superseded
    await db.execute(
        update(Plan)
        .where(Plan.child_id == child.id, Plan.status == "active")
        .values(status="superseded")
    )

    # 2. 计算版本号（P1-3: 使用 COUNT 代替全量加载）
    count_result = await db.execute(
        select(func.count()).select_from(Plan).where(Plan.child_id == child.id)
    )
    version = (count_result.scalar() or 0) + 1

    today = date.today()

    # 3. 创建 Plan
    plan = Plan(
        child_id=child.id,
        version=version,
        status="active",
        title=ai_result.get("title", ""),
        primary_goal=ai_result.get("primary_goal", ""),
        focus_theme=ai_result.get("focus_theme", child.focus_themes[0] if child.focus_themes else "language"),
        priority_scenes=ai_result.get("priority_scenes", []),
        stage=child.stage,
        risk_level_at_creation=child.risk_level,
        start_date=today,
        end_date=today + timedelta(days=6),
        current_day=1,
        completion_rate=0.0,
        observation_candidates=ai_result.get("observation_candidates"),
        weekend_review_prompt=ai_result.get("weekend_review_prompt"),
        conservative_note=ai_result.get("conservative_note"),
        ai_generation_id=ai_session.id,
    )
    db.add(plan)
    await db.flush()

    # 4. 创建 7 个 DayTask
    day_tasks_data = ai_result.get("day_tasks", [])
    for dt_data in day_tasks_data:
        day_task = DayTask(
            plan_id=plan.id,
            day_number=dt_data.get("day_number", 1),
            main_exercise_title=dt_data.get("main_exercise_title", ""),
            main_exercise_description=dt_data.get("main_exercise_description", ""),
            natural_embed_title=dt_data.get("natural_embed_title", ""),
            natural_embed_description=dt_data.get("natural_embed_description", ""),
            demo_script=dt_data.get("demo_script", ""),
            observation_point=dt_data.get("observation_point", ""),
            completion_status=CompletionStatus.PENDING.value,
        )
        db.add(day_task)

    await db.flush()
    await db.refresh(plan)
    return plan


async def update_day_task_completion(
    db: AsyncSession,
    plan_id: uuid.UUID,
    day_number: int,
    completion_status: str,
) -> tuple[DayTask | None, Plan | None]:
    """更新日任务完成状态，并重算计划完成率。

    Returns:
        (updated_day_task, updated_plan) 或 (None, None) 如果未找到。
    """
    # 获取计划及其日任务
    plan = await get_plan(db, plan_id)
    if plan is None:
        return None, None

    # 找到目标日任务
    target_task: DayTask | None = None
    for task in plan.day_tasks:
        if task.day_number == day_number:
            target_task = task
            break

    if target_task is None:
        return None, None

    # 更新完成状态
    target_task.completion_status = completion_status
    if completion_status in (
        CompletionStatus.EXECUTED.value,
        CompletionStatus.PARTIAL.value,
    ):
        target_task.completed_at = datetime.now(timezone.utc)
    elif completion_status == CompletionStatus.PENDING.value:
        target_task.completed_at = None

    # 重算完成率
    completed_count = sum(
        1
        for t in plan.day_tasks
        if t.completion_status
        in (CompletionStatus.EXECUTED.value, CompletionStatus.PARTIAL.value)
    )
    # P2-2: 使用实际 day_tasks 数量代替硬编码 7
    total_tasks = len(plan.day_tasks) or 7
    plan.completion_rate = completed_count / total_tasks

    await db.flush()
    await db.refresh(target_task)
    await db.refresh(plan)
    return target_task, plan


async def get_today_task(
    db: AsyncSession, plan: Plan
) -> DayTask | None:
    """获取当前计划的今日任务。"""
    for task in plan.day_tasks:
        if task.day_number == plan.current_day:
            return task
    return None


async def list_plans(
    db: AsyncSession,
    child_id: uuid.UUID,
    limit: int = 20,
    offset: int = 0,
) -> tuple[list[Plan], int]:
    """获取儿童的所有计划列表（按创建时间降序）。

    Returns:
        (plans, total_count)
    """
    from sqlalchemy import func

    # 总数
    count_result = await db.execute(
        select(func.count()).select_from(Plan).where(Plan.child_id == child_id)
    )
    total = count_result.scalar() or 0

    # 分页查询
    result = await db.execute(
        select(Plan)
        .where(Plan.child_id == child_id)
        .order_by(Plan.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    plans = list(result.scalars().all())
    return plans, total


async def append_focus_note(
    db: AsyncSession, plan_id: uuid.UUID, note: str
) -> Plan | None:
    """将关注内容追加到计划的 next_week_context 字段。

    采用追加式写入，不覆盖已有内容。多条关注项以换行分隔。

    Returns:
        更新后的 Plan，如果未找到则返回 None。
    """
    plan = await get_plan(db, plan_id)
    if plan is None:
        return None

    existing = plan.next_week_context or ""
    separator = "\n" if existing else ""
    plan.next_week_context = existing + separator + note

    plan.updated_at = datetime.now(timezone.utc)
    await db.flush()
    await db.refresh(plan)
    return plan


async def advance_all_plans(db: AsyncSession) -> dict:
    """推进所有活跃计划的 current_day。

    每日零点调用，执行以下逻辑：
    - current_day < 7 → current_day + 1（批量 SQL）
    - current_day >= 7 → status 设为 "completed"（批量 SQL）

    对推进到第 7 天的计划单独查询以触发周反馈。

    Returns:
        统计信息字典 {"advanced": N, "completed": N}
    """
    now = datetime.now(timezone.utc)

    # P1-4: 批量 SQL 完成计划（current_day >= 7）
    completed_result = await db.execute(
        update(Plan)
        .where(Plan.status == "active", Plan.current_day >= 7)
        .values(status="completed", updated_at=now)
    )
    completed_count = completed_result.rowcount  # type: ignore[union-attr]

    # P1-4: 批量 SQL 推进普通计划（current_day < 7）
    advanced_result = await db.execute(
        update(Plan)
        .where(Plan.status == "active", Plan.current_day < 7)
        .values(current_day=Plan.current_day + 1, updated_at=now)
    )
    advanced_count = advanced_result.rowcount  # type: ignore[union-attr]

    # 查询推进到第 7 天的计划（用于触发周反馈）
    result = await db.execute(
        select(Plan).where(Plan.status == "active", Plan.current_day == 7)
    )
    plans_reaching_day7 = list(result.scalars().all())

    await db.flush()

    logger.info(
        "Plan day advancement: advanced=%d, completed=%d, reaching_day7=%d",
        advanced_count,
        completed_count,
        len(plans_reaching_day7),
    )

    return {
        "advanced": advanced_count,
        "completed": completed_count,
        "plans_reaching_day7": plans_reaching_day7,
    }
