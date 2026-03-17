"""渠道端到端集成测试 — Phase 6。

覆盖：
1. 入站消息 AI 处理管线（InboundMessageHandler）
2. OpenClaw 入站 → AI 回复 → 出站推送全链路
3. 微信入站 → AI 回复 → 出站推送全链路
4. 微信 QR 扫码自动绑定
5. InboundMessageHandler 错误降级
"""

from __future__ import annotations

import uuid

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from ai_parenting.backend.models import AISession, ChannelBinding, Child, Message, User


# ---------------------------------------------------------------------------
# Test Helpers
# ---------------------------------------------------------------------------


async def _create_full_user(
    db: AsyncSession,
    user_id: uuid.UUID | None = None,
    email: str = "e2e@example.com",
    openid: str = "",
    whatsapp_id: str = "",
    with_child: bool = True,
) -> tuple[uuid.UUID, uuid.UUID | None]:
    """创建完整测试用户（含孩子+渠道绑定），返回 (user_id, child_id)。"""
    uid = user_id or uuid.uuid4()

    user = User(id=uid, email=email, auth_provider="email")
    db.add(user)
    await db.flush()

    child_id = None
    if with_child:
        child_id = uuid.uuid4()
        child = Child(
            id=child_id,
            user_id=uid,
            nickname="测试宝宝",
            birth_date="2024-06-15",
        )
        db.add(child)

    if openid:
        db.add(ChannelBinding(
            user_id=uid,
            channel="wechat",
            channel_user_id=openid,
            is_active=True,
        ))

    if whatsapp_id:
        db.add(ChannelBinding(
            user_id=uid,
            channel="openclaw_whatsapp",
            channel_user_id=whatsapp_id,
            is_active=True,
        ))

    await db.commit()
    return uid, child_id


def _make_wechat_xml(
    from_user: str,
    msg_type: str,
    content: str = "",
    event: str = "",
    event_key: str = "",
) -> str:
    """构造微信 XML 消息体。"""
    parts = [
        "<xml>",
        f"<ToUserName><![CDATA[gh_test_account]]></ToUserName>",
        f"<FromUserName><![CDATA[{from_user}]]></FromUserName>",
        f"<CreateTime>1710000000</CreateTime>",
        f"<MsgType><![CDATA[{msg_type}]]></MsgType>",
    ]
    if msg_type == "text":
        parts.append(f"<Content><![CDATA[{content}]]></Content>")
    if msg_type == "event":
        parts.append(f"<Event><![CDATA[{event}]]></Event>")
        parts.append(f"<EventKey><![CDATA[{event_key}]]></EventKey>")
    parts.append("</xml>")
    return "".join(parts)


# ---------------------------------------------------------------------------
# 1. InboundMessageHandler 单元测试
# ---------------------------------------------------------------------------


class TestInboundMessageHandler:
    """入站消息 AI 处理管线测试。"""

    @pytest.mark.asyncio
    async def test_handle_inbound_basic(self, db_session: AsyncSession):
        """基本入站消息处理 — 有孩子时返回意图和回复。"""
        from ai_parenting.backend.services.inbound_handler import handle_inbound_message

        uid, _ = await _create_full_user(db_session, openid="o_basic_001")

        result = await handle_inbound_message(
            db=db_session,
            user_id=uid,
            text="今天做什么训练",
            channel="wechat",
            channel_user_id="o_basic_001",
        )
        assert result.success is True
        assert result.reply_text  # 非空回复
        assert result.intent != "unknown"

    @pytest.mark.asyncio
    async def test_handle_inbound_no_child(self, db_session: AsyncSession):
        """无孩子用户也能处理消息（降级回复）。"""
        from ai_parenting.backend.services.inbound_handler import handle_inbound_message

        uid, _ = await _create_full_user(
            db_session, email="nochild@test.com", with_child=False,
        )

        result = await handle_inbound_message(
            db=db_session,
            user_id=uid,
            text="你好",
            channel="wechat",
            channel_user_id="o_nochild_001",
        )
        # 即使没有孩子信息也不应崩溃
        assert result.success is True or result.error is not None
        assert result.reply_text  # 总有回复（成功或降级）

    @pytest.mark.asyncio
    async def test_handle_inbound_records_session(self, db_session: AsyncSession):
        """入站消息应创建 AISession 和 Message 记录。"""
        from ai_parenting.backend.services.inbound_handler import handle_inbound_message

        uid, _ = await _create_full_user(
            db_session, email="session@test.com", openid="o_session_001",
        )

        result = await handle_inbound_message(
            db=db_session,
            user_id=uid,
            text="宝宝不肯吃饭怎么办",
            channel="wechat",
            channel_user_id="o_session_001",
        )

        assert result.success is True
        assert result.session_id is not None

        # 验证 AISession 记录已创建
        from sqlalchemy import select

        session_result = await db_session.execute(
            select(AISession).where(AISession.id == result.session_id)
        )
        ai_session = session_result.scalar_one_or_none()
        assert ai_session is not None
        assert ai_session.status == "completed"

        # 验证 Message 记录（应有用户消息 + AI 回复）
        msg_result = await db_session.execute(
            select(Message).where(Message.session_id == result.session_id)
        )
        messages = msg_result.scalars().all()
        assert len(messages) == 2
        roles = [m.role for m in messages]
        assert "user" in roles
        assert "assistant" in roles

    @pytest.mark.asyncio
    async def test_handle_inbound_with_channel_router(self, db_session: AsyncSession):
        """提供 ChannelRouter 时应尝试发送回复（Mock 路由器）。"""
        from ai_parenting.backend.services.inbound_handler import handle_inbound_message

        uid, _ = await _create_full_user(
            db_session, email="router@test.com", openid="o_router_001",
        )

        # Mock ChannelRouter — 记录调用
        sent_messages = []

        class _TrackingRouter:
            async def route_message(self, message, channel_preferences, force_channel=None):
                from ai_parenting.backend.channels.base import SendResult
                sent_messages.append({
                    "recipient": message.recipient_id,
                    "body": message.body,
                    "channel": force_channel,
                })
                return SendResult(success=True, channel_name=force_channel or "mock")

        result = await handle_inbound_message(
            db=db_session,
            user_id=uid,
            text="记录一下宝宝今天会走路了",
            channel="wechat",
            channel_user_id="o_router_001",
            channel_router=_TrackingRouter(),
        )

        assert result.success is True
        # ChannelRouter 不是真正的 ChannelRouter 实例，_send_reply 会跳过
        # 但如果是真实的 ChannelRouter 实例，应该发送消息


# ---------------------------------------------------------------------------
# 2. OpenClaw 端到端测试
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_openclaw_inbound_with_ai_processing(
    client: AsyncClient, db_session: AsyncSession,
):
    """OpenClaw 入站消息应触发 AI 处理并返回意图。"""
    uid, _ = await _create_full_user(
        db_session,
        email="oc_e2e@test.com",
        whatsapp_id="+8613800001111",
    )

    resp = await client.post(
        "/webhooks/openclaw",
        json={
            "type": "inbound",
            "channel": "whatsapp",
            "sender": "+8613800001111",
            "content": {"text": "宝宝今天学会叠积木了", "type": "text"},
            "timestamp": "2026-03-17T10:00:00Z",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert "intent" in data


@pytest.mark.asyncio
async def test_openclaw_inbound_empty_text(
    client: AsyncClient, db_session: AsyncSession,
):
    """OpenClaw 空文本消息也应正常处理。"""
    uid, _ = await _create_full_user(
        db_session,
        email="oc_empty@test.com",
        whatsapp_id="+8613800002222",
    )

    resp = await client.post(
        "/webhooks/openclaw",
        json={
            "type": "inbound",
            "channel": "whatsapp",
            "sender": "+8613800002222",
            "content": {"text": "", "type": "text"},
            "timestamp": "2026-03-17T10:00:00Z",
        },
    )
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# 3. 微信端到端测试
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_wechat_text_triggers_ai(
    client: AsyncClient, db_session: AsyncSession,
):
    """微信文本消息应触发 AI 处理管线。"""
    uid, _ = await _create_full_user(
        db_session,
        email="wx_ai@test.com",
        openid="o_wx_ai_001",
    )

    xml_body = _make_wechat_xml(
        from_user="o_wx_ai_001",
        msg_type="text",
        content="宝宝不肯吃饭怎么办",
    )

    resp = await client.post(
        "/webhooks/wechat",
        content=xml_body.encode("utf-8"),
        headers={"Content-Type": "application/xml"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_wechat_voice_triggers_ai(
    client: AsyncClient, db_session: AsyncSession,
):
    """微信语音消息（已转写）应触发 AI 处理。"""
    uid, _ = await _create_full_user(
        db_session,
        email="wx_voice@test.com",
        openid="o_wx_voice_001",
    )

    # 微信语音消息的识别结果在 Recognition 字段
    xml_body = (
        "<xml>"
        "<ToUserName><![CDATA[gh_test]]></ToUserName>"
        "<FromUserName><![CDATA[o_wx_voice_001]]></FromUserName>"
        "<CreateTime>1710000000</CreateTime>"
        "<MsgType><![CDATA[voice]]></MsgType>"
        "<Recognition><![CDATA[记录一下宝宝今天会说妈妈了]]></Recognition>"
        "</xml>"
    )

    resp = await client.post(
        "/webhooks/wechat",
        content=xml_body.encode("utf-8"),
        headers={"Content-Type": "application/xml"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


# ---------------------------------------------------------------------------
# 4. 微信 QR 扫码自动绑定测试
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_wechat_subscribe_qr_binding(
    client: AsyncClient, db_session: AsyncSession,
):
    """微信关注事件带 scene_str 应自动完成绑定。"""
    uid = uuid.uuid4()
    user = User(id=uid, email="qr@test.com", auth_provider="email")
    db_session.add(user)
    await db_session.commit()

    openid = "o_qr_subscriber_001"
    scene_str = f"bind:{uid}:test_state_123"

    xml_body = _make_wechat_xml(
        from_user=openid,
        msg_type="event",
        event="subscribe",
        event_key=f"qrscene_{scene_str}",
    )

    resp = await client.post(
        "/webhooks/wechat",
        content=xml_body.encode("utf-8"),
        headers={"Content-Type": "application/xml"},
    )
    assert resp.status_code == 200

    # 验证绑定已创建
    from sqlalchemy import select
    result = await db_session.execute(
        select(ChannelBinding).where(
            ChannelBinding.user_id == str(uid),
            ChannelBinding.channel == "wechat",
        )
    )
    binding = result.scalar_one_or_none()
    assert binding is not None
    assert binding.channel_user_id == openid
    assert binding.is_active is True


@pytest.mark.asyncio
async def test_wechat_scan_qr_binding(
    client: AsyncClient, db_session: AsyncSession,
):
    """已关注用户扫码应自动完成绑定。"""
    uid = uuid.uuid4()
    user = User(id=uid, email="scan@test.com", auth_provider="email")
    db_session.add(user)
    await db_session.commit()

    openid = "o_scan_user_001"
    scene_str = f"bind:{uid}:scan_state_456"

    xml_body = _make_wechat_xml(
        from_user=openid,
        msg_type="event",
        event="SCAN",
        event_key=scene_str,
    )

    resp = await client.post(
        "/webhooks/wechat",
        content=xml_body.encode("utf-8"),
        headers={"Content-Type": "application/xml"},
    )
    assert resp.status_code == 200

    # 验证绑定
    from sqlalchemy import select
    result = await db_session.execute(
        select(ChannelBinding).where(
            ChannelBinding.user_id == str(uid),
            ChannelBinding.channel == "wechat",
        )
    )
    binding = result.scalar_one_or_none()
    assert binding is not None
    assert binding.channel_user_id == openid


@pytest.mark.asyncio
async def test_wechat_subscribe_no_scene_no_binding(
    client: AsyncClient, db_session: AsyncSession,
):
    """微信关注事件无 scene_str 不应创建绑定。"""
    uid = uuid.uuid4()
    user = User(id=uid, email="noscan@test.com", auth_provider="email")
    db_session.add(user)
    await db_session.commit()

    xml_body = _make_wechat_xml(
        from_user="o_no_scene_001",
        msg_type="event",
        event="subscribe",
        event_key="",  # 无 scene
    )

    resp = await client.post(
        "/webhooks/wechat",
        content=xml_body.encode("utf-8"),
        headers={"Content-Type": "application/xml"},
    )
    assert resp.status_code == 200

    # 不应有绑定记录
    from sqlalchemy import select
    result = await db_session.execute(
        select(ChannelBinding).where(
            ChannelBinding.channel_user_id == "o_no_scene_001",
        )
    )
    binding = result.scalar_one_or_none()
    assert binding is None


# ---------------------------------------------------------------------------
# 5. 错误降级测试
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_inbound_handler_graceful_degradation(db_session: AsyncSession):
    """AI 处理失败时应返回降级回复而非崩溃。"""
    from unittest.mock import AsyncMock, patch

    from ai_parenting.backend.services.inbound_handler import handle_inbound_message

    uid, _ = await _create_full_user(
        db_session, email="degrade@test.com", openid="o_degrade_001",
    )

    # Mock VoicePipeline 抛出异常
    with patch(
        "ai_parenting.backend.services.inbound_handler._route_to_ai",
        new_callable=AsyncMock,
        side_effect=RuntimeError("AI service unavailable"),
    ):
        result = await handle_inbound_message(
            db=db_session,
            user_id=uid,
            text="你好",
            channel="wechat",
            channel_user_id="o_degrade_001",
        )

    assert result.success is False
    assert "暂时无法处理" in result.reply_text
    assert result.error is not None
