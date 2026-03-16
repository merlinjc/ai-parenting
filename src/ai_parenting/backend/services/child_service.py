"""儿童档案服务。

实现儿童档案的 CRUD 操作，含阶段自动计算和关注主题管理。
"""

from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ai_parenting.backend.models import Child
from ai_parenting.backend.schemas import ChildCreate, ChildUpdate
from ai_parenting.models.enums import ChildStage


def _compute_age_months(birth_year_month: str) -> int:
    """根据出生年月计算当前月龄。"""
    today = date.today()
    parts = birth_year_month.split("-")
    birth_year, birth_month = int(parts[0]), int(parts[1])
    months = (today.year - birth_year) * 12 + (today.month - birth_month)
    return max(18, min(48, months))


def _compute_stage(age_months: int) -> str:
    """根据月龄映射阶段。"""
    if age_months < 24:
        return ChildStage.M18_24.value
    elif age_months < 36:
        return ChildStage.M24_36.value
    else:
        return ChildStage.M36_48.value


async def create_child(
    db: AsyncSession, user_id: uuid.UUID, data: ChildCreate
) -> Child:
    """创建儿童档案，自动计算月龄和阶段。"""
    age_months = _compute_age_months(data.birth_year_month)
    stage = _compute_stage(age_months)

    child = Child(
        user_id=user_id,
        nickname=data.nickname,
        birth_year_month=data.birth_year_month,
        age_months=age_months,
        stage=stage,
        focus_themes=data.focus_themes or [],
        risk_level=data.risk_level,
        onboarding_completed=False,
    )
    db.add(child)
    await db.flush()
    await db.refresh(child)
    return child


async def get_child(db: AsyncSession, child_id: uuid.UUID) -> Child | None:
    """按 ID 获取儿童档案。"""
    result = await db.execute(select(Child).where(Child.id == child_id))
    return result.scalar_one_or_none()


async def get_children_by_user(
    db: AsyncSession, user_id: uuid.UUID
) -> list[Child]:
    """获取用户下所有儿童档案。"""
    result = await db.execute(
        select(Child).where(Child.user_id == user_id).order_by(Child.created_at)
    )
    return list(result.scalars().all())


async def update_child(
    db: AsyncSession, child_id: uuid.UUID, data: ChildUpdate
) -> Child | None:
    """更新儿童档案。"""
    child = await get_child(db, child_id)
    if child is None:
        return None

    if data.nickname is not None:
        child.nickname = data.nickname
    if data.focus_themes is not None:
        child.focus_themes = data.focus_themes
    if data.risk_level is not None:
        child.risk_level = data.risk_level

    await db.flush()
    await db.refresh(child)
    return child


async def refresh_age_and_stage(db: AsyncSession, child_id: uuid.UUID) -> Child | None:
    """刷新儿童月龄和阶段（登录时或定时调用）。"""
    child = await get_child(db, child_id)
    if child is None:
        return None

    child.age_months = _compute_age_months(child.birth_year_month)
    child.stage = _compute_stage(child.age_months)

    await db.flush()
    await db.refresh(child)
    return child


async def complete_onboarding(db: AsyncSession, child_id: uuid.UUID) -> Child | None:
    """标记儿童已完成首次引导。"""
    child = await get_child(db, child_id)
    if child is None:
        return None
    child.onboarding_completed = True
    await db.flush()
    await db.refresh(child)
    return child
