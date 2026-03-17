"""观察记录路由。

提供记录的创建、列表查询（含分页和类型过滤）API。
"""

from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from ai_parenting.backend.auth import get_current_user_id
from ai_parenting.backend.database import get_db
from ai_parenting.backend.schemas import RecordCreate, RecordListResponse, RecordResponse
from ai_parenting.backend.services import record_service
from ai_parenting.backend.services.child_service import get_child

router = APIRouter(prefix="/records", tags=["records"])


async def _verify_child_ownership(
    db: AsyncSession, user_id: uuid.UUID, child_id: uuid.UUID
) -> None:
    """校验 child_id 属于当前用户，否则抛出 403。"""
    child = await get_child(db, child_id)
    if child is None:
        raise HTTPException(status_code=404, detail="Child not found")
    if child.user_id != user_id:
        raise HTTPException(status_code=403, detail="无权操作此儿童的数据")


@router.post("", response_model=RecordResponse, status_code=201)
async def create_record(
    body: RecordCreate,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> RecordResponse:
    """创建观察记录。"""
    await _verify_child_ownership(db, user_id, body.child_id)
    record = await record_service.create_record(db, body)
    return RecordResponse.model_validate(record)


@router.get("", response_model=RecordListResponse)
async def list_records(
    child_id: uuid.UUID = Query(..., description="儿童 ID"),
    limit: int = Query(20, ge=1, le=100),
    before: datetime | None = Query(None, description="分页游标：返回此时间之前的记录"),
    type: str | None = Query(None, description="记录类型过滤"),
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> RecordListResponse:
    """查询记录列表（按时间倒序，支持分页和类型过滤）。"""
    await _verify_child_ownership(db, user_id, child_id)
    records, has_more, total = await record_service.list_records(
        db, child_id, limit=limit, before=before, record_type=type
    )
    return RecordListResponse(
        records=[RecordResponse.model_validate(r) for r in records],
        has_more=has_more,
        total=total,
    )


@router.get("/{record_id}", response_model=RecordResponse)
async def get_record(
    record_id: uuid.UUID,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> RecordResponse:
    """获取单条记录详情。"""
    record = await record_service.get_record(db, record_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Record not found")
    # 校验记录所属儿童的所有权
    child = await get_child(db, record.child_id)
    if child is None or child.user_id != user_id:
        raise HTTPException(status_code=403, detail="无权访问此记录")
    return RecordResponse.model_validate(record)
