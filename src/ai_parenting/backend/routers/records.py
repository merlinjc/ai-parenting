"""观察记录路由。

提供记录的创建、列表查询（含分页和类型过滤）API。
"""

from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from ai_parenting.backend.database import get_db
from ai_parenting.backend.schemas import RecordCreate, RecordListResponse, RecordResponse
from ai_parenting.backend.services import record_service

router = APIRouter(prefix="/records", tags=["records"])


@router.post("", response_model=RecordResponse, status_code=201)
async def create_record(
    body: RecordCreate,
    db: AsyncSession = Depends(get_db),
) -> RecordResponse:
    """创建观察记录。"""
    record = await record_service.create_record(db, body)
    return RecordResponse.model_validate(record)


@router.get("", response_model=RecordListResponse)
async def list_records(
    child_id: uuid.UUID = Query(..., description="儿童 ID"),
    limit: int = Query(20, ge=1, le=100),
    before: datetime | None = Query(None, description="分页游标：返回此时间之前的记录"),
    type: str | None = Query(None, description="记录类型过滤"),
    db: AsyncSession = Depends(get_db),
) -> RecordListResponse:
    """查询记录列表（按时间倒序，支持分页和类型过滤）。"""
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
    db: AsyncSession = Depends(get_db),
) -> RecordResponse:
    """获取单条记录详情。"""
    record = await record_service.get_record(db, record_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Record not found")
    return RecordResponse.model_validate(record)
