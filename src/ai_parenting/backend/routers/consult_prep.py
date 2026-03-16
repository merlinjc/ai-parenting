"""咨询准备路由。

提供聚合的就诊/咨询准备数据端点。
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from ai_parenting.backend.auth import get_current_user_id
from ai_parenting.backend.database import get_db
from ai_parenting.backend.services.consult_prep_service import get_consult_prep_data

router = APIRouter(prefix="/consult-prep", tags=["consult-prep"])


@router.get("")
async def get_consult_prep(
    child_id: uuid.UUID = Query(..., description="儿童 ID"),
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """获取咨询准备数据。

    聚合最近观察记录、AI 咨询建议和就诊准备清单。
    """
    try:
        data = await get_consult_prep_data(db, child_id)
        return data
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
