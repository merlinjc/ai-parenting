"""渠道绑定业务服务。

提供渠道绑定、解绑、偏好排序更新、微信 OAuth 绑定等业务逻辑。
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ai_parenting.backend.models import ChannelBinding, Device, UserChannelPreference

logger = logging.getLogger(__name__)

# P2-3: 允许的渠道名称白名单
ALLOWED_CHANNELS = frozenset({"apns", "wechat", "whatsapp", "telegram", "openclaw"})


# ---------------------------------------------------------------------------
# 渠道绑定 CRUD
# ---------------------------------------------------------------------------


async def get_user_bindings(
    db: AsyncSession,
    user_id: uuid.UUID,
) -> list[ChannelBinding]:
    """获取用户的所有渠道绑定。"""
    result = await db.execute(
        select(ChannelBinding)
        .where(ChannelBinding.user_id == str(user_id))
        .order_by(ChannelBinding.created_at)
    )
    return list(result.scalars().all())


async def bind_channel(
    db: AsyncSession,
    user_id: uuid.UUID,
    channel: str,
    channel_user_id: str,
    device_id: uuid.UUID | None = None,
    display_label: str | None = None,
) -> ChannelBinding:
    """绑定渠道。

    如果该渠道已绑定，更新 channel_user_id 和 display_label。
    如果是新绑定，自动将渠道追加到用户偏好列表。

    对于 APNs 渠道，验证 device_id 指向的 Device 存在。
    """
    # P2-3: 渠道名称白名单校验
    if channel not in ALLOWED_CHANNELS:
        raise ValueError(f"Invalid channel: '{channel}'. Allowed: {', '.join(sorted(ALLOWED_CHANNELS))}")

    # APNs 渠道：验证 device 存在
    if channel == "apns" and device_id:
        device = await db.get(Device, str(device_id))
        if device is None:
            raise ValueError(f"Device {device_id} not found")
        # 使用 device 的 push_token 作为 channel_user_id
        if device.push_token:
            channel_user_id = device.push_token

    # 查找是否已绑定
    result = await db.execute(
        select(ChannelBinding).where(
            ChannelBinding.user_id == str(user_id),
            ChannelBinding.channel == channel,
        )
    )
    existing = result.scalar_one_or_none()

    if existing:
        # 更新已有绑定
        existing.channel_user_id = channel_user_id
        existing.device_id = device_id
        existing.display_label = display_label or existing.display_label
        existing.is_active = True
        existing.verified_at = datetime.now(timezone.utc)
        logger.info(
            "Updated channel binding: user=%s channel=%s",
            user_id, channel,
        )
        return existing

    # 创建新绑定
    binding = ChannelBinding(
        user_id=user_id,
        channel=channel,
        channel_user_id=channel_user_id,
        device_id=device_id,
        display_label=display_label,
        is_active=True,
        verified_at=datetime.now(timezone.utc),
    )
    db.add(binding)

    # 自动追加到用户渠道偏好
    await _append_channel_to_preference(db, user_id, channel)

    logger.info(
        "Created channel binding: user=%s channel=%s",
        user_id, channel,
    )
    return binding


async def unbind_channel(
    db: AsyncSession,
    user_id: uuid.UUID,
    binding_id: uuid.UUID,
) -> bool:
    """解绑渠道。

    软删除：将 is_active 设为 False。
    同时从用户渠道偏好中移除该渠道。

    Returns:
        True 如果成功解绑，False 如果绑定不存在。
    """
    result = await db.execute(
        select(ChannelBinding).where(
            ChannelBinding.id == str(binding_id),
            ChannelBinding.user_id == str(user_id),
        )
    )
    binding = result.scalar_one_or_none()
    if binding is None:
        return False

    binding.is_active = False

    # 从偏好中移除
    await _remove_channel_from_preference(db, user_id, binding.channel)

    logger.info(
        "Unbound channel: user=%s channel=%s binding_id=%s",
        user_id, binding.channel, binding_id,
    )
    return True


# ---------------------------------------------------------------------------
# 渠道偏好管理
# ---------------------------------------------------------------------------


async def get_channel_preference(
    db: AsyncSession,
    user_id: uuid.UUID,
) -> UserChannelPreference:
    """获取用户渠道偏好（不存在时自动创建默认偏好）。"""
    result = await db.execute(
        select(UserChannelPreference).where(
            UserChannelPreference.user_id == str(user_id)
        )
    )
    pref = result.scalar_one_or_none()

    if pref is None:
        # 自动创建默认偏好
        pref = UserChannelPreference(
            user_id=user_id,
            channel_priority=["apns"],
            quiet_start_hour=22,
            quiet_end_hour=8,
            max_daily_pushes=5,
        )
        db.add(pref)
        logger.info("Created default channel preference for user=%s", user_id)

    return pref


async def update_channel_preference(
    db: AsyncSession,
    user_id: uuid.UUID,
    *,
    channel_priority: list[str] | None = None,
    quiet_start_hour: int | None = None,
    quiet_end_hour: int | None = None,
    max_daily_pushes: int | None = None,
) -> UserChannelPreference:
    """更新用户渠道偏好。

    仅更新传入的非 None 字段。
    如果 channel_priority 中包含用户未绑定的渠道，忽略该渠道。
    """
    pref = await get_channel_preference(db, user_id)

    if channel_priority is not None:
        # 验证：只保留用户已绑定且激活的渠道
        active_bindings = await get_user_bindings(db, user_id)
        active_channels = {b.channel for b in active_bindings if b.is_active}
        pref.channel_priority = [ch for ch in channel_priority if ch in active_channels]
        if not pref.channel_priority:
            # 至少保留一个兜底渠道
            pref.channel_priority = ["apns"] if "apns" in active_channels else list(active_channels)[:1]

    if quiet_start_hour is not None:
        pref.quiet_start_hour = quiet_start_hour
    if quiet_end_hour is not None:
        pref.quiet_end_hour = quiet_end_hour
    if max_daily_pushes is not None:
        pref.max_daily_pushes = max_daily_pushes

    logger.info("Updated channel preference: user=%s", user_id)
    return pref


async def get_user_channel_priorities(
    db: AsyncSession,
    user_id: uuid.UUID,
) -> list[str]:
    """获取用户的渠道优先级列表（供 ChannelRouter 使用）。

    如果用户没有设置偏好，返回默认 ["apns"]。
    """
    pref = await get_channel_preference(db, user_id)
    return pref.channel_priority if pref.channel_priority else ["apns"]


# ---------------------------------------------------------------------------
# 内部辅助方法
# ---------------------------------------------------------------------------


async def _append_channel_to_preference(
    db: AsyncSession,
    user_id: uuid.UUID,
    channel: str,
) -> None:
    """将新渠道追加到用户偏好列表（如果不存在）。"""
    pref = await get_channel_preference(db, user_id)
    if channel not in pref.channel_priority:
        pref.channel_priority = [*pref.channel_priority, channel]


async def _remove_channel_from_preference(
    db: AsyncSession,
    user_id: uuid.UUID,
    channel: str,
) -> None:
    """从用户偏好列表中移除渠道。"""
    pref = await get_channel_preference(db, user_id)
    if channel in pref.channel_priority:
        pref.channel_priority = [ch for ch in pref.channel_priority if ch != channel]
        # 确保至少保留一个渠道
        if not pref.channel_priority:
            pref.channel_priority = ["apns"]


# ---------------------------------------------------------------------------
# 微信 OAuth 绑定
# ---------------------------------------------------------------------------


async def generate_wechat_qrcode_state(
    db: AsyncSession,
    user_id: uuid.UUID,
) -> dict:
    """生成微信绑定的二维码。

    优先使用微信公众平台「带参数临时二维码」API（用户扫码关注/回复即绑定）；
    如果微信凭据未配置，降级为 OAuth 链接方式。

    Returns:
        {"qrcode_url": "...", "state": "...", "expires_in": 300}
    """
    import httpx

    from ai_parenting.backend.config import settings

    state = uuid.uuid4().hex[:16]

    if not (settings.wechat_app_id and settings.wechat_app_secret):
        # 未配置微信凭据，返回 OAuth 链接（降级模式）
        # P2-14: redirect_uri 从配置读取
        redirect_uri = getattr(settings, "wechat_oauth_redirect_uri",
                               "https://api.aiparenting.com/webhooks/wechat/oauth")
        import urllib.parse
        encoded_redirect = urllib.parse.quote(redirect_uri, safe="")
        return {
            "qrcode_url": (
                f"https://open.weixin.qq.com/connect/oauth2/authorize"
                f"?appid={settings.wechat_app_id}"
                f"&redirect_uri={encoded_redirect}"
                f"&response_type=code&scope=snsapi_base&state={state}#wechat_redirect"
            ),
            "state": state,
            "expires_in": 300,
        }

    # 生产模式：通过微信 API 获取带参数临时二维码
    # scene_str 编码绑定信息，扫码后微信回调 webhook 会携带此 scene_str
    scene_str = f"bind:{user_id}:{state}"

    try:
        # 1. 获取 access_token
        token_url = (
            f"https://api.weixin.qq.com/cgi-bin/token"
            f"?grant_type=client_credential"
            f"&appid={settings.wechat_app_id}"
            f"&secret={settings.wechat_app_secret}"
        )
        async with httpx.AsyncClient(timeout=10.0) as client:
            token_resp = await client.get(token_url)
            token_data = token_resp.json()
            access_token = token_data.get("access_token")
            if not access_token:
                raise RuntimeError(f"WeChat token error: {token_data}")

            # 2. 创建带参数临时二维码（5 分钟有效）
            qr_url = f"https://api.weixin.qq.com/cgi-bin/qrcode/create?access_token={access_token}"
            qr_resp = await client.post(qr_url, json={
                "expire_seconds": 300,
                "action_name": "QR_STR_SCENE",
                "action_info": {"scene": {"scene_str": scene_str}},
            })
            qr_data = qr_resp.json()
            ticket = qr_data.get("ticket")
            if not ticket:
                raise RuntimeError(f"WeChat QR error: {qr_data}")

            # 3. 用 ticket 换取二维码图片 URL
            qrcode_url = f"https://mp.weixin.qq.com/cgi-bin/showqrcode?ticket={ticket}"

            return {
                "qrcode_url": qrcode_url,
                "state": state,
                "scene_str": scene_str,
                "expires_in": 300,
            }
    except Exception as exc:
        # API 调用失败，降级为 OAuth 链接
        import logging
        import urllib.parse
        logging.getLogger(__name__).warning("WeChat QR API failed, falling back: %s", exc)
        redirect_uri = getattr(settings, "wechat_oauth_redirect_uri",
                               "https://api.aiparenting.com/webhooks/wechat/oauth")
        encoded_redirect = urllib.parse.quote(redirect_uri, safe="")
        return {
            "qrcode_url": (
                f"https://open.weixin.qq.com/connect/oauth2/authorize"
                f"?appid={settings.wechat_app_id}"
                f"&redirect_uri={encoded_redirect}"
                f"&response_type=code&scope=snsapi_base&state={state}#wechat_redirect"
            ),
            "state": state,
            "expires_in": 300,
        }


async def handle_wechat_oauth_callback(
    db: AsyncSession,
    user_id: uuid.UUID,
    openid: str,
    nickname: str | None = None,
) -> ChannelBinding:
    """处理微信 OAuth 回调，完成绑定。

    Args:
        db: 数据库会话。
        user_id: 当前用户 ID。
        openid: 微信用户的 openid。
        nickname: 微信昵称（可选）。

    Returns:
        创建或更新的 ChannelBinding。
    """
    return await bind_channel(
        db,
        user_id=user_id,
        channel="wechat",
        channel_user_id=openid,
        display_label=nickname,
    )
