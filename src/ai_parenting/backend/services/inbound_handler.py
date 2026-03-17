"""入站消息 AI 处理管线。

接收来自外部渠道（微信/WhatsApp/Telegram）的用户消息，
执行意图分类 → Skill 路由 → 生成 AI 回复 → 通过原渠道回传。

核心流程：
  1. 查找用户绑定 → 确定 user_id 和首个孩子
  2. VoicePipeline 意图分类 + Skill 路由（复用语音管线逻辑）
  3. 通过 ChannelRouter 将回复推送回原渠道
  4. 记录消息日志（AISession + Message）

设计决策：
- 复用 VoicePipeline 作为意图分类和 Skill 路由引擎（已有 5 种指令支持）
- 入站消息视为"文本模式的语音对话"（跳过 ASR/TTS 环节）
- 回复通过 ChannelRouter.route_message() 发送，强制使用原渠道
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ai_parenting.backend.channels.base import ChannelMessage, MessageType
from ai_parenting.backend.models import AISession, Child, Message

logger = logging.getLogger(__name__)


@dataclass
class InboundResult:
    """入站消息处理结果。"""

    success: bool
    reply_text: str
    intent: str = "unknown"
    error: str | None = None
    session_id: str | None = None
    record_id: str | None = None
    latency_ms: int = 0


async def handle_inbound_message(
    db: AsyncSession,
    user_id: uuid.UUID,
    text: str,
    channel: str,
    channel_user_id: str,
    *,
    channel_router: object | None = None,
) -> InboundResult:
    """处理一条入站消息的完整管线。

    Args:
        db: 数据库会话。
        user_id: 已绑定的用户 ID。
        text: 用户发来的文本内容。
        channel: 来源渠道名（wechat / openclaw_whatsapp / openclaw_telegram）。
        channel_user_id: 渠道内用户标识（openid / WhatsApp 号码等）。
        channel_router: ChannelRouter 实例，用于回传回复消息。

    Returns:
        InboundResult 包含处理结果和回复文本。
    """
    import time

    start = time.monotonic()

    try:
        # 1. 查找用户的首个孩子（用于 Skill 上下文）
        child = await _get_first_child(db, user_id)
        child_id = str(child.id) if child else ""

        # 2. 通过 VoicePipeline 进行意图分类 + Skill 路由
        reply_text, intent, record_id = await _route_to_ai(
            db=db,
            user_id=user_id,
            child_id=child_id,
            text=text,
        )

        # 3. 记录 AI 对话到 AISession + Message
        session_id = await _record_session(
            db=db,
            user_id=user_id,
            child_id=child_id,
            user_text=text,
            ai_reply=reply_text,
            channel=channel,
            intent=intent,
        )
        await db.commit()

        # 4. 通过原渠道回传回复
        if channel_router is not None and reply_text:
            await _send_reply(
                channel_router=channel_router,
                channel=channel,
                channel_user_id=channel_user_id,
                reply_text=reply_text,
            )

        elapsed = int((time.monotonic() - start) * 1000)
        logger.info(
            "Inbound handled: user=%s channel=%s intent=%s latency=%dms",
            user_id, channel, intent, elapsed,
        )
        return InboundResult(
            success=True,
            reply_text=reply_text,
            intent=intent,
            session_id=session_id,
            record_id=record_id,
            latency_ms=elapsed,
        )

    except Exception as exc:
        elapsed = int((time.monotonic() - start) * 1000)
        logger.error(
            "Inbound handling failed: user=%s channel=%s error=%s",
            user_id, channel, exc, exc_info=True,
        )
        # 降级回复 — 不让用户等待无响应
        fallback_reply = "抱歉，我暂时无法处理您的消息。请稍后再试，或打开 App 获取帮助。"
        if channel_router is not None:
            try:
                await _send_reply(
                    channel_router=channel_router,
                    channel=channel,
                    channel_user_id=channel_user_id,
                    reply_text=fallback_reply,
                )
            except Exception:
                logger.error("Failed to send fallback reply", exc_info=True)

        return InboundResult(
            success=False,
            reply_text=fallback_reply,
            error=str(exc),
            latency_ms=elapsed,
        )


# ---------------------------------------------------------------------------
# 内部方法
# ---------------------------------------------------------------------------


async def _get_first_child(
    db: AsyncSession,
    user_id: uuid.UUID,
) -> Child | None:
    """查找用户的首个孩子（按创建时间排序）。"""
    result = await db.execute(
        select(Child)
        .where(Child.user_id == str(user_id))
        .order_by(Child.created_at)
        .limit(1)
    )
    return result.scalar_one_or_none()


async def _route_to_ai(
    db: AsyncSession,
    user_id: uuid.UUID,
    child_id: str,
    text: str,
) -> tuple[str, str, str | None]:
    """通过 VoicePipeline 进行意图分类和 Skill 路由。

    Returns:
        (reply_text, intent, record_id)
    """
    from ai_parenting.backend.services.voice_service import process_voice_converse

    result = await process_voice_converse(
        transcript=text,
        child_id=uuid.UUID(child_id) if child_id else uuid.UUID(int=0),
        confidence=1.0,  # 文本输入不需要 ASR 置信度判断
        db=db,
        user_id=user_id,
    )
    return result.reply_text, result.intent, result.record_id


async def _record_session(
    db: AsyncSession,
    user_id: uuid.UUID,
    child_id: str,
    user_text: str,
    ai_reply: str,
    channel: str,
    intent: str,
) -> str:
    """记录一次渠道对话到 AISession + Message 表。

    Returns:
        session_id
    """
    session_id = uuid.uuid4()

    # 创建 AISession（session_type 复用 instant_help，标记来源渠道）
    session = AISession(
        id=session_id,
        user_id=user_id,
        child_id=child_id if child_id else None,
        session_type="instant_help",
        status="completed",
        metadata_={"source_channel": channel, "intent": intent},
    )
    db.add(session)

    # 用户消息
    user_msg = Message(
        id=uuid.uuid4(),
        session_id=session_id,
        role="user",
        content=user_text,
    )
    db.add(user_msg)

    # AI 回复
    ai_msg = Message(
        id=uuid.uuid4(),
        session_id=session_id,
        role="assistant",
        content=ai_reply,
    )
    db.add(ai_msg)

    return str(session_id)


async def _send_reply(
    channel_router: object,
    channel: str,
    channel_user_id: str,
    reply_text: str,
) -> None:
    """通过 ChannelRouter 将回复推送回原渠道。"""
    from ai_parenting.backend.channels.router import ChannelRouter

    if not isinstance(channel_router, ChannelRouter):
        logger.warning("channel_router is not a ChannelRouter instance, skipping reply")
        return

    message = ChannelMessage(
        recipient_id=channel_user_id,
        title="",
        body=reply_text,
        message_type=MessageType.TEXT,
    )

    # 强制使用原渠道发送（不走偏好优先级）
    result = await channel_router.route_message(
        message,
        channel_preferences=[channel],
        force_channel=channel,
    )

    if result.success:
        logger.info(
            "Reply sent via %s to %s (latency=%dms)",
            channel, channel_user_id[:8] + "...", result.latency_ms or 0,
        )
    else:
        logger.error(
            "Failed to send reply via %s: %s",
            channel, result.error,
        )
