"""观察记录服务。

实现记录的创建、查询、按周聚合等操作。
创建记录时自动联动更新关联计划的 DayTask 完成状态。
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ai_parenting.backend.models import Record
from ai_parenting.backend.schemas import RecordCreate

logger = logging.getLogger(__name__)


async def create_record(db: AsyncSession, data: RecordCreate) -> Record:
    """创建观察记录，并联动更新关联计划的 DayTask 完成状态。"""
    record = Record(
        child_id=data.child_id,
        type=data.type,
        tags=data.tags,
        content=data.content,
        voice_url=data.voice_url,
        transcript=data.transcript,
        scene=data.scene,
        time_of_day=data.time_of_day,
        theme=data.theme,
        source_plan_id=data.source_plan_id,
        source_session_id=data.source_session_id,
        synced_to_plan=False,
    )
    db.add(record)
    await db.flush()
    await db.refresh(record)

    # Gap 8: 记录关联了计划时，自动回写 DayTask 完成状态
    if data.source_plan_id is not None:
        try:
            from ai_parenting.backend.services.plan_service import (
                get_plan,
                update_day_task_completion,
            )
            from ai_parenting.models.enums import CompletionStatus

            plan = await get_plan(db, data.source_plan_id)
            if plan is not None and plan.status == "active":
                day_task, updated_plan = await update_day_task_completion(
                    db,
                    plan_id=plan.id,
                    day_number=plan.current_day,
                    completion_status=CompletionStatus.EXECUTED.value,
                )
                if day_task is not None:
                    record.synced_to_plan = True
                    await db.flush()
                    await db.refresh(record)
                    logger.info(
                        "Record %s synced to DayTask day=%d of plan %s",
                        record.id,
                        plan.current_day,
                        plan.id,
                    )
        except Exception:
            logger.exception(
                "Failed to sync record %s to plan DayTask", record.id
            )
            # 不因联动失败阻断记录创建

    return record


async def get_record(db: AsyncSession, record_id: uuid.UUID) -> Record | None:
    """按 ID 获取记录。"""
    result = await db.execute(select(Record).where(Record.id == record_id))
    return result.scalar_one_or_none()


async def list_records(
    db: AsyncSession,
    child_id: uuid.UUID,
    limit: int = 20,
    before: datetime | None = None,
    record_type: str | None = None,
) -> tuple[list[Record], bool, int]:
    """查询记录列表（按时间倒序，支持分页和类型过滤）。

    Returns:
        (records, has_more, total)
    """
    query = select(Record).where(Record.child_id == child_id)

    if before is not None:
        query = query.where(Record.created_at < before)
    if record_type is not None:
        query = query.where(Record.type == record_type)

    # 总数
    count_query = (
        select(func.count())
        .select_from(Record)
        .where(Record.child_id == child_id)
    )
    if record_type is not None:
        count_query = count_query.where(Record.type == record_type)
    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    # 分页查询（多取一条判断 has_more）
    query = query.order_by(Record.created_at.desc()).limit(limit + 1)
    result = await db.execute(query)
    records = list(result.scalars().all())

    has_more = len(records) > limit
    if has_more:
        records = records[:limit]

    return records, has_more, total


async def get_recent_records(
    db: AsyncSession, child_id: uuid.UUID, count: int = 3
) -> list[Record]:
    """获取最近 N 条记录。"""
    result = await db.execute(
        select(Record)
        .where(Record.child_id == child_id)
        .order_by(Record.created_at.desc())
        .limit(count)
    )
    return list(result.scalars().all())


async def get_weekly_records(
    db: AsyncSession, child_id: uuid.UUID, week_start: datetime
) -> list[Record]:
    """获取指定周的所有记录（按周聚合）。"""
    week_end = week_start + timedelta(days=7)
    result = await db.execute(
        select(Record)
        .where(
            Record.child_id == child_id,
            Record.created_at >= week_start,
            Record.created_at < week_end,
        )
        .order_by(Record.created_at)
    )
    return list(result.scalars().all())


async def count_weekly_records(
    db: AsyncSession, child_id: uuid.UUID, week_start: datetime
) -> int:
    """统计指定周的记录数量。"""
    week_end = week_start + timedelta(days=7)
    result = await db.execute(
        select(func.count())
        .select_from(Record)
        .where(
            Record.child_id == child_id,
            Record.created_at >= week_start,
            Record.created_at < week_end,
        )
    )
    return result.scalar_one()
