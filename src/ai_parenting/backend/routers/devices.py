"""设备注册与管理路由。

提供设备注册/更新端点，用于推送令牌上报和设备信息登记。
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ai_parenting.backend.auth import get_current_user_id
from ai_parenting.backend.database import get_db
from ai_parenting.backend.models import Device, User
from ai_parenting.backend.schemas import DeviceRegisterRequest, DeviceResponse

router = APIRouter(prefix="/devices", tags=["devices"])


@router.post("", response_model=DeviceResponse, status_code=201)
async def register_device(
    body: DeviceRegisterRequest,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> DeviceResponse:
    """注册或更新设备信息。

    如果用户在同一平台已有活跃设备，则更新其 push_token 和 app_version；
    否则创建新的设备记录。
    """
    # 确保用户存在
    user_result = await db.execute(select(User).where(User.id == user_id))
    user = user_result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    # 查找该用户在同一平台的现有活跃设备
    device_result = await db.execute(
        select(Device).where(
            Device.user_id == user_id,
            Device.platform == body.platform,
            Device.is_active == True,  # noqa: E712
        )
    )
    existing_device = device_result.scalar_one_or_none()

    now = datetime.now(timezone.utc)

    if existing_device:
        # 更新已有设备
        existing_device.push_token = body.push_token
        existing_device.app_version = body.app_version
        existing_device.last_active_at = now
        await db.flush()
        await db.refresh(existing_device)
        return DeviceResponse.model_validate(existing_device)
    else:
        # 创建新设备
        device = Device(
            user_id=user_id,
            push_token=body.push_token,
            platform=body.platform,
            app_version=body.app_version,
            last_active_at=now,
            is_active=True,
        )
        db.add(device)
        await db.flush()
        await db.refresh(device)
        return DeviceResponse.model_validate(device)
