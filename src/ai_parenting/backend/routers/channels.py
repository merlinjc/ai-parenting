"""渠道管理 API 路由。

提供渠道绑定 CRUD、偏好管理和微信 OAuth 绑定相关端点。

端点列表：
- GET    /channels              — 获取当前用户已绑定的渠道列表
- POST   /channels/bind         — 绑定新渠道
- DELETE /channels/{binding_id}  — 解绑渠道
- GET    /channels/preferences  — 获取渠道偏好设置
- PATCH  /channels/preferences  — 更新渠道偏好排序和静默时段
- GET    /channels/wechat/qrcode — 获取微信 OAuth 绑定二维码
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from ai_parenting.backend.auth import get_current_user_id
from ai_parenting.backend.database import get_db
from ai_parenting.backend.schemas import (
    ChannelBindingCreate,
    ChannelBindingListResponse,
    ChannelBindingResponse,
    ChannelPreferenceResponse,
    ChannelPreferenceUpdate,
    WeChatQRCodeResponse,
)
from ai_parenting.backend.services import channel_binding_service

router = APIRouter(prefix="/channels", tags=["channels"])


# ---------------------------------------------------------------------------
# 渠道绑定
# ---------------------------------------------------------------------------


@router.get("", response_model=ChannelBindingListResponse)
async def list_bindings(
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> ChannelBindingListResponse:
    """获取当前用户已绑定的所有渠道。"""
    bindings = await channel_binding_service.get_user_bindings(db, user_id)
    return ChannelBindingListResponse(
        bindings=[ChannelBindingResponse.model_validate(b) for b in bindings if b.is_active]
    )


@router.post("/bind", response_model=ChannelBindingResponse, status_code=status.HTTP_201_CREATED)
async def bind_channel(
    body: ChannelBindingCreate,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> ChannelBindingResponse:
    """绑定新渠道。

    如果该渠道已绑定，更新 channel_user_id。
    APNs 渠道需提供 device_id 关联已注册设备。
    """
    try:
        binding = await channel_binding_service.bind_channel(
            db,
            user_id=user_id,
            channel=body.channel,
            channel_user_id=body.channel_user_id,
            device_id=body.device_id,
            display_label=body.display_label,
        )
        await db.commit()
        await db.refresh(binding)
        return ChannelBindingResponse.model_validate(binding)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.delete("/{binding_id}", status_code=status.HTTP_204_NO_CONTENT)
async def unbind_channel(
    binding_id: uuid.UUID,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> None:
    """解绑渠道（软删除）。"""
    success = await channel_binding_service.unbind_channel(db, user_id, binding_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Channel binding not found",
        )
    await db.commit()


# ---------------------------------------------------------------------------
# 渠道偏好
# ---------------------------------------------------------------------------


@router.get("/preferences", response_model=ChannelPreferenceResponse)
async def get_preferences(
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> ChannelPreferenceResponse:
    """获取当前用户的渠道偏好设置。"""
    pref = await channel_binding_service.get_channel_preference(db, user_id)
    await db.commit()  # 如果是首次自动创建，需要提交
    return ChannelPreferenceResponse.model_validate(pref)


@router.put("/preferences", response_model=ChannelPreferenceResponse)
async def update_preferences(
    body: ChannelPreferenceUpdate,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> ChannelPreferenceResponse:
    """更新渠道偏好（优先级排序、静默时段、每日推送上限）。"""
    pref = await channel_binding_service.update_channel_preference(
        db,
        user_id,
        channel_priority=body.channel_priority,
        quiet_start_hour=body.quiet_start_hour,
        quiet_end_hour=body.quiet_end_hour,
        max_daily_pushes=body.max_daily_pushes,
    )
    await db.commit()
    await db.refresh(pref)
    return ChannelPreferenceResponse.model_validate(pref)


# ---------------------------------------------------------------------------
# 微信 OAuth 绑定
# ---------------------------------------------------------------------------


@router.get("/wechat/qrcode", response_model=WeChatQRCodeResponse)
async def get_wechat_qrcode(
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> WeChatQRCodeResponse:
    """获取微信 OAuth 绑定二维码。

    返回二维码 URL 和 state 参数，iOS 端展示二维码供用户扫描。
    扫码后微信将回调到 webhooks 端点完成绑定。
    """
    data = await channel_binding_service.generate_wechat_qrcode_state(db, user_id)
    return WeChatQRCodeResponse(**data)
