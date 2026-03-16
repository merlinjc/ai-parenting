"""消息路由。

提供消息列表查询、详情、状态更新、未读计数和点击回流端点。
消息创建通过内部服务调用完成，不暴露公开 API。
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Header, Query
from sqlalchemy.ext.asyncio import AsyncSession

from ai_parenting.backend.database import get_db
from ai_parenting.backend.schemas import (
    MessageListResponse,
    MessageResponse,
    MessageUpdateRequest,
    UnreadCountResponse,
)
from ai_parenting.backend.services import message_service

router = APIRouter(prefix="/messages", tags=["messages"])


# ---------------------------------------------------------------------------
# 临时鉴权（复用 children 路由的模式）
# ---------------------------------------------------------------------------

_DEFAULT_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


def _get_user_id(x_user_id: str | None = Header(None, alias="X-User-Id")) -> uuid.UUID:
    if x_user_id:
        return uuid.UUID(x_user_id)
    return _DEFAULT_USER_ID


# ---------------------------------------------------------------------------
# 端点
# ---------------------------------------------------------------------------


@router.get("", response_model=MessageListResponse)
async def list_messages(
    limit: int = Query(20, ge=1, le=50),
    before: Optional[datetime] = Query(None),
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(_get_user_id),
):
    """获取消息列表（分页，未处理优先排序）。"""
    messages, has_more = await message_service.list_messages(
        db, user_id, limit=limit, before=before,
    )
    total_unread = await message_service.get_unread_count(db, user_id)
    return MessageListResponse(
        messages=[MessageResponse.model_validate(m) for m in messages],
        has_more=has_more,
        total_unread=total_unread,
    )


@router.get("/unread-count", response_model=UnreadCountResponse)
async def get_unread_count(
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(_get_user_id),
):
    """获取未读消息计数。"""
    count = await message_service.get_unread_count(db, user_id)
    return UnreadCountResponse(unread_count=count)


@router.get("/{message_id}", response_model=MessageResponse)
async def get_message(
    message_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """获取消息详情。"""
    message = await message_service.get_message(db, message_id)
    if not message:
        raise HTTPException(status_code=404, detail="消息不存在")
    return MessageResponse.model_validate(message)


@router.patch("/{message_id}", response_model=MessageResponse)
async def update_message_status(
    message_id: uuid.UUID,
    body: MessageUpdateRequest,
    db: AsyncSession = Depends(get_db),
):
    """更新消息阅读状态。"""
    message = await message_service.update_read_status(
        db, message_id, body.read_status,
    )
    if not message:
        raise HTTPException(status_code=404, detail="消息不存在")
    return MessageResponse.model_validate(message)


@router.post("/{message_id}/clicked", response_model=MessageResponse)
async def record_message_click(
    message_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """记录消息点击事件（客户端上报）。"""
    message = await message_service.record_click(db, message_id)
    if not message:
        raise HTTPException(status_code=404, detail="消息不存在")
    return MessageResponse.model_validate(message)


@router.post("/{message_id}/delivered", response_model=MessageResponse)
async def record_message_delivered(
    message_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """记录推送送达事件（客户端上报）。"""
    message = await message_service.get_message(db, message_id)
    if not message:
        raise HTTPException(status_code=404, detail="消息不存在")
    message.push_delivered_at = datetime.now(timezone.utc)
    message.push_status = "delivered"
    await db.flush()
    return MessageResponse.model_validate(message)
