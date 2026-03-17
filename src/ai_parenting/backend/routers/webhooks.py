"""第三方回调 Webhook 路由。

接收微信公众平台消息/事件回调和 OpenClaw Gateway 入站消息转发。

端点列表：
- GET  /webhooks/wechat      — 微信服务器验证（echostr 回调）
- POST /webhooks/wechat      — 微信消息/事件回调处理
- POST /webhooks/openclaw    — OpenClaw Gateway 入站消息转发
"""

from __future__ import annotations

import hashlib
import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ai_parenting.backend.config import settings
from ai_parenting.backend.database import get_db
from ai_parenting.backend.deps import get_channel_router
from ai_parenting.backend.models import ChannelBinding
from ai_parenting.backend.services import channel_binding_service
from ai_parenting.backend.services.inbound_handler import handle_inbound_message

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


# ---------------------------------------------------------------------------
# 微信公众号回调
# ---------------------------------------------------------------------------


@router.get("/wechat")
async def wechat_verify(
    signature: str = Query(...),
    timestamp: str = Query(...),
    nonce: str = Query(...),
    echostr: str = Query(...),
) -> int | str:
    """微信服务器验证（Token 校验）。

    微信在配置服务器 URL 时会发 GET 请求，需返回 echostr 确认。
    """
    if not _verify_wechat_signature(signature, timestamp, nonce):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid signature",
        )
    return echostr


@router.post("/wechat")
async def wechat_callback(
    request: Request,
    signature: str = Query(""),
    timestamp: str = Query(""),
    nonce: str = Query(""),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """微信消息/事件回调。

    处理以下事件类型：
    - text/voice: 用户发送的文本/语音消息 → 路由到 AI 处理
    - event:subscribe: 用户关注事件 → 可触发绑定流程
    - event:SCAN: 扫码事件 → 用于 OAuth 绑定确认
    """
    # 签名验证（生产环境必须启用）
    if settings.wechat_token and not _verify_wechat_signature(signature, timestamp, nonce):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid signature",
        )

    # 解析请求体（微信发送的是 XML 格式）
    body = await request.body()
    payload = _parse_wechat_xml(body.decode("utf-8"))

    msg_type = payload.get("MsgType", "")
    from_user = payload.get("FromUserName", "")

    logger.info(
        "WeChat callback: type=%s, from=%s",
        msg_type, from_user[:8] + "..." if from_user else "unknown",
    )

    # 处理关注/扫码事件 — 可能触发 OAuth 绑定
    if msg_type == "event":
        event = payload.get("Event", "")
        event_key = payload.get("EventKey", "")
        await _handle_wechat_event(db, from_user, event, event_key)
        await db.commit()

    # 处理文本/语音消息 — 路由到 AI 处理
    elif msg_type in ("text", "voice"):
        await _handle_wechat_message(db, from_user, payload)

    return {"status": "ok"}


# ---------------------------------------------------------------------------
# OpenClaw Gateway 入站消息
# ---------------------------------------------------------------------------


@router.post("/openclaw")
async def openclaw_callback(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """OpenClaw Gateway 入站消息转发。

    接收来自 WhatsApp/Telegram 等渠道经 OpenClaw Gateway 转发的用户消息。

    payload 格式:
    {
        "type": "inbound",
        "channel": "whatsapp" | "telegram",
        "sender": "channel_user_id",
        "content": {"text": "...", "type": "text"},
        "timestamp": "2026-03-17T10:00:00Z",
        "signature": "hmac_sha256_hex"
    }
    """
    payload: dict[str, Any] = await request.json()

    # 验证消息签名
    if settings.openclaw_api_key:
        provided_sig = payload.get("signature", "")
        if not _verify_openclaw_signature(payload, provided_sig):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid OpenClaw signature",
            )

    msg_type = payload.get("type")
    if msg_type != "inbound":
        logger.debug("Ignoring non-inbound OpenClaw message: type=%s", msg_type)
        return {"status": "ignored"}

    channel = payload.get("channel", "unknown")
    sender = payload.get("sender", "")
    content = payload.get("content", {})
    text = content.get("text", "")

    logger.info(
        "OpenClaw inbound: channel=%s, sender=%s, text_len=%d",
        channel, sender[:8] + "..." if sender else "unknown", len(text),
    )

    # 查找对应的用户绑定
    binding = await _find_binding_by_channel_user(
        db,
        channel=f"openclaw_{channel}" if channel in ("whatsapp", "telegram") else channel,
        channel_user_id=sender,
    )

    if binding is None:
        logger.warning(
            "No binding found for OpenClaw sender: channel=%s, sender=%s",
            channel, sender,
        )
        return {"status": "no_binding"}

    # 路由到 AI 处理管线
    channel_router = get_channel_router()
    channel_key = f"openclaw_{channel}" if channel in ("whatsapp", "telegram") else channel
    result = await handle_inbound_message(
        db=db,
        user_id=binding.user_id,
        text=text,
        channel=channel_key,
        channel_user_id=sender,
        channel_router=channel_router,
    )
    logger.info(
        "OpenClaw message processed: user=%s intent=%s latency=%dms",
        binding.user_id, result.intent, result.latency_ms,
    )

    return {"status": "ok", "intent": result.intent}


# ---------------------------------------------------------------------------
# 内部辅助函数
# ---------------------------------------------------------------------------


def _verify_wechat_signature(signature: str, timestamp: str, nonce: str) -> bool:
    """验证微信消息签名。"""
    token = settings.wechat_token
    if not token:
        return True  # 未配置 token 时跳过验证（开发环境）

    params = sorted([token, timestamp, nonce])
    computed = hashlib.sha1("".join(params).encode()).hexdigest()
    return computed == signature


def _parse_wechat_xml(xml_str: str) -> dict[str, str]:
    """简易 XML 解析（微信消息格式固定，无需完整 XML parser）。

    解析 <xml><Key>Value</Key>...</xml> 格式。
    """
    import re

    result: dict[str, str] = {}
    # 匹配 <Key>Value</Key> 和 <Key><![CDATA[Value]]></Key>
    pattern = re.compile(r"<(\w+)>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</\1>", re.DOTALL)
    for match in pattern.finditer(xml_str):
        key, value = match.group(1), match.group(2).strip()
        if key != "xml":
            result[key] = value
    return result


def _verify_openclaw_signature(payload: dict[str, Any], signature: str) -> bool:
    """验证 OpenClaw 消息 HMAC-SHA256 签名。"""
    import hmac

    if not settings.openclaw_api_key:
        return True  # 未配置 API Key 时跳过验证

    # 构造待签名字符串（排除 signature 字段）
    sign_data = {k: v for k, v in payload.items() if k != "signature"}
    sign_str = "&".join(f"{k}={v}" for k, v in sorted(sign_data.items()))

    expected = hmac.new(
        settings.openclaw_api_key.encode(),
        sign_str.encode(),
        hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(expected, signature)


async def _find_binding_by_channel_user(
    db: AsyncSession,
    channel: str,
    channel_user_id: str,
) -> ChannelBinding | None:
    """根据渠道和渠道用户 ID 查找绑定关系。"""
    result = await db.execute(
        select(ChannelBinding).where(
            ChannelBinding.channel == channel,
            ChannelBinding.channel_user_id == channel_user_id,
            ChannelBinding.is_active.is_(True),
        )
    )
    return result.scalar_one_or_none()


async def _handle_wechat_event(
    db: AsyncSession,
    openid: str,
    event: str,
    event_key: str,
) -> None:
    """处理微信事件（关注/扫码等）。"""
    if event == "subscribe":
        logger.info("WeChat user subscribed: openid=%s, event_key=%s", openid[:8] + "...", event_key)
        # 如果 event_key 包含绑定 state，触发自动绑定
        if event_key and event_key.startswith("qrscene_"):
            state = event_key.replace("qrscene_", "")
            logger.info("OAuth binding triggered via subscribe: state=%s", state)
            await _handle_qr_binding(db, openid, state)

    elif event == "SCAN":
        logger.info("WeChat scan event: openid=%s, event_key=%s", openid[:8] + "...", event_key)
        # 已关注用户扫码 — 直接触发绑定
        if event_key:
            logger.info("OAuth binding triggered via scan: state=%s", event_key)
            await _handle_qr_binding(db, openid, event_key)

    elif event == "unsubscribe":
        logger.info("WeChat user unsubscribed: openid=%s", openid[:8] + "...")
        # 取消关注 → 停用微信渠道绑定
        binding = await _find_binding_by_channel_user(db, "wechat", openid)
        if binding:
            binding.is_active = False
            logger.info("Deactivated WeChat binding for openid=%s", openid[:8] + "...")


async def _handle_wechat_message(
    db: AsyncSession,
    openid: str,
    payload: dict[str, str],
) -> None:
    """处理微信用户发来的文本/语音消息。"""
    msg_type = payload.get("MsgType", "")
    content = payload.get("Content", "") if msg_type == "text" else payload.get("Recognition", "")

    # 查找用户绑定
    binding = await _find_binding_by_channel_user(db, "wechat", openid)
    if binding is None:
        logger.warning("No binding for WeChat openid=%s, ignoring message", openid[:8] + "...")
        return

    logger.info(
        "WeChat message from user=%s: type=%s, content_len=%d",
        binding.user_id, msg_type, len(content),
    )

    # 路由到 AI 处理管线
    channel_router = get_channel_router()
    result = await handle_inbound_message(
        db=db,
        user_id=binding.user_id,
        text=content,
        channel="wechat",
        channel_user_id=openid,
        channel_router=channel_router,
    )
    logger.info(
        "WeChat message processed: user=%s intent=%s latency=%dms",
        binding.user_id, result.intent, result.latency_ms,
    )


async def _handle_qr_binding(
    db: AsyncSession,
    openid: str,
    scene_str: str,
) -> None:
    """处理微信二维码扫码绑定。

    scene_str 格式：``bind:{user_id}:{state}``
    由 channel_binding_service.generate_wechat_qrcode_state() 生成。
    """
    import uuid as _uuid

    if not scene_str.startswith("bind:"):
        logger.debug("Ignoring non-binding scene_str: %s", scene_str[:32])
        return

    parts = scene_str.split(":")
    if len(parts) < 3:
        logger.warning("Malformed binding scene_str: %s", scene_str[:32])
        return

    try:
        user_id = _uuid.UUID(parts[1])
    except ValueError:
        logger.warning("Invalid user_id in scene_str: %s", parts[1])
        return

    # 调用 channel_binding_service 完成绑定
    binding = await channel_binding_service.handle_wechat_oauth_callback(
        db=db,
        user_id=user_id,
        openid=openid,
        nickname=None,  # 微信关注事件不携带昵称
    )
    logger.info(
        "WeChat QR binding completed: user=%s openid=%s binding_id=%s",
        user_id, openid[:8] + "...", binding.id,
    )
