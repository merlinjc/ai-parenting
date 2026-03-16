"""用户档案路由。

提供用户 Profile 的 GET/PATCH API。
当前版本使用 X-User-Id header 模拟鉴权。
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ai_parenting.backend.database import get_db
from ai_parenting.backend.models import User
from ai_parenting.backend.schemas import (
    ChildResponse,
    UserProfileResponse,
    UserProfileUpdate,
)

router = APIRouter(prefix="/user", tags=["user"])

_DEFAULT_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


def _get_user_id(x_user_id: str | None = Header(None)) -> uuid.UUID:
    """从请求头获取用户 ID，缺失时使用默认值。"""
    if x_user_id:
        try:
            return uuid.UUID(x_user_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid X-User-Id header")
    return _DEFAULT_USER_ID


@router.get("/profile", response_model=UserProfileResponse)
async def get_profile(
    user_id: uuid.UUID = Depends(_get_user_id),
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
    user_id: uuid.UUID = Depends(_get_user_id),
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
    await db.commit()
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
