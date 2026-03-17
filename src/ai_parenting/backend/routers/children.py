"""儿童档案路由。

提供儿童档案的 CRUD API。
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from ai_parenting.backend.auth import get_current_user_id
from ai_parenting.backend.database import get_db
from ai_parenting.backend.schemas import ChildCreate, ChildResponse, ChildUpdate
from ai_parenting.backend.services import child_service

router = APIRouter(prefix="/children", tags=["children"])


@router.post("", response_model=ChildResponse, status_code=201)
async def create_child(
    body: ChildCreate,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> ChildResponse:
    """创建儿童档案。"""
    child = await child_service.create_child(db, user_id, body)
    return ChildResponse.model_validate(child)


@router.get("", response_model=list[ChildResponse])
async def list_children(
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> list[ChildResponse]:
    """列出用户下所有儿童档案。"""
    children = await child_service.get_children_by_user(db, user_id)
    return [ChildResponse.model_validate(c) for c in children]


@router.get("/{child_id}", response_model=ChildResponse)
async def get_child(
    child_id: uuid.UUID,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> ChildResponse:
    """获取单个儿童档案。"""
    child = await child_service.get_child(db, child_id)
    if child is None:
        raise HTTPException(status_code=404, detail="Child not found")
    return ChildResponse.model_validate(child)


@router.patch("/{child_id}", response_model=ChildResponse)
async def update_child(
    child_id: uuid.UUID,
    body: ChildUpdate,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> ChildResponse:
    """更新儿童档案。"""
    child = await child_service.update_child(db, child_id, body)
    if child is None:
        raise HTTPException(status_code=404, detail="Child not found")
    return ChildResponse.model_validate(child)


@router.post("/{child_id}/refresh-stage", response_model=ChildResponse)
async def refresh_stage(
    child_id: uuid.UUID,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> ChildResponse:
    """刷新儿童月龄和阶段。"""
    child = await child_service.refresh_age_and_stage(db, child_id)
    if child is None:
        raise HTTPException(status_code=404, detail="Child not found")
    return ChildResponse.model_validate(child)


@router.post("/{child_id}/complete-onboarding", response_model=ChildResponse)
async def complete_onboarding(
    child_id: uuid.UUID,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> ChildResponse:
    """标记儿童完成首次引导。"""
    child = await child_service.complete_onboarding(db, child_id)
    if child is None:
        raise HTTPException(status_code=404, detail="Child not found")
    return ChildResponse.model_validate(child)
