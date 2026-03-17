"""用户档案路由。

提供用户 Profile 的 GET/PATCH API。
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ai_parenting.backend.auth import get_current_user_id
from ai_parenting.backend.database import get_db
from ai_parenting.backend.models import User
from ai_parenting.backend.schemas import (
    ChildResponse,
    UserProfileResponse,
    UserProfileUpdate,
)

router = APIRouter(prefix="/user", tags=["user"])


@router.get("/profile", response_model=UserProfileResponse)
async def get_profile(
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> UserProfileResponse:
    """获取当前用户档案（含儿童列表）。"""
    stmt = (
        select(User)
        .options(selectinload(User.children))
        .where(User.id == user_id)
    )
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    # 手动构建响应以包含 children
    children_resp = [ChildResponse.model_validate(c) for c in user.children]
    return UserProfileResponse(
        id=user.id,
        display_name=user.display_name,
        caregiver_role=user.caregiver_role,
        timezone=user.timezone,
        push_enabled=user.push_enabled,
        created_at=user.created_at,
        updated_at=user.updated_at,
        children=children_resp,
    )


@router.patch("/profile", response_model=UserProfileResponse)
async def update_profile(
    body: UserProfileUpdate,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> UserProfileResponse:
    """更新当前用户档案。"""
    stmt = (
        select(User)
        .options(selectinload(User.children))
        .where(User.id == user_id)
    )
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(user, field, value)
    await db.flush()  # P1-13: 使用 flush 而非 commit，保持事务一致性
    await db.refresh(user)

    children_resp = [ChildResponse.model_validate(c) for c in user.children]
    return UserProfileResponse(
        id=user.id,
        display_name=user.display_name,
        caregiver_role=user.caregiver_role,
        timezone=user.timezone,
        push_enabled=user.push_enabled,
        created_at=user.created_at,
        updated_at=user.updated_at,
        children=children_resp,
    )
