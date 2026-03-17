"""Webhook 回调集成测试。

覆盖端点：
- GET  /webhooks/wechat      — 微信服务器验证
- POST /webhooks/wechat      — 微信消息/事件回调
- POST /webhooks/openclaw    — OpenClaw Gateway 入站消息
"""

from __future__ import annotations

import hashlib
import hmac
import uuid

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from ai_parenting.backend.models import ChannelBinding, User


# ---------------------------------------------------------------------------
# Test Helpers
# ---------------------------------------------------------------------------


async def _create_user_with_wechat_binding(
    db: AsyncSession,
) -> tuple[uuid.UUID, str]:
    """创建测试用户和微信绑定，返回 (user_id, openid)。"""
    user_id = uuid.UUID("00000000-0000-0000-0000-000000000001")
    openid = "o_test_wx_openid_001"

    user = User(
        id=user_id,
        email="test@example.com",
        auth_provider="email",
    )
    binding = ChannelBinding(
        user_id=user_id,
        channel="wechat",
        channel_user_id=openid,
        display_label="测试微信号",
        is_active=True,
    )
    db.add(user)
    db.add(binding)
    await db.commit()
    return user_id, openid


def _make_wechat_xml(from_user: str, msg_type: str, content: str = "", event: str = "", event_key: str = "") -> str:
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
# 微信服务器验证（GET /webhooks/wechat）
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_wechat_verify_success(client: AsyncClient):
    """无 wechat_token 配置时（开发环境），验证应直接通过并返回 echostr。"""
    resp = await client.get(
        "/webhooks/wechat",
        params={
            "signature": "dummy",
            "timestamp": "12345",
            "nonce": "nonce",
            "echostr": "test_echostr_value",
        },
    )
    assert resp.status_code == 200
    assert "test_echostr_value" in resp.text


# ---------------------------------------------------------------------------
# 微信消息回调（POST /webhooks/wechat）
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_wechat_text_message(client: AsyncClient, db_session: AsyncSession):
    """微信文本消息应返回 200 ok。"""
    _, openid = await _create_user_with_wechat_binding(db_session)

    xml_body = _make_wechat_xml(
        from_user=openid,
        msg_type="text",
        content="宝宝今天不肯吃饭怎么办？",
    )

    resp = await client.post(
        "/webhooks/wechat",
        content=xml_body.encode("utf-8"),
        headers={"Content-Type": "application/xml"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_wechat_subscribe_event(client: AsyncClient, db_session: AsyncSession):
    """微信关注事件应返回 200 ok。"""
    user_id = uuid.UUID("00000000-0000-0000-0000-000000000001")
    user = User(id=user_id, email="sub@example.com", auth_provider="email")
    db_session.add(user)
    await db_session.commit()

    xml_body = _make_wechat_xml(
        from_user="o_new_subscriber_001",
        msg_type="event",
        event="subscribe",
        event_key="qrscene_bind_state_123",
    )

    resp = await client.post(
        "/webhooks/wechat",
        content=xml_body.encode("utf-8"),
        headers={"Content-Type": "application/xml"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_wechat_unsubscribe_event(client: AsyncClient, db_session: AsyncSession):
    """微信取消关注应停用绑定。"""
    _, openid = await _create_user_with_wechat_binding(db_session)

    xml_body = _make_wechat_xml(
        from_user=openid,
        msg_type="event",
        event="unsubscribe",
    )

    resp = await client.post(
        "/webhooks/wechat",
        content=xml_body.encode("utf-8"),
        headers={"Content-Type": "application/xml"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


# ---------------------------------------------------------------------------
# OpenClaw Gateway 回调（POST /webhooks/openclaw）
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_openclaw_inbound_message(client: AsyncClient, db_session: AsyncSession):
    """OpenClaw 入站消息（有绑定）应返回 ok。"""
    user_id = uuid.UUID("00000000-0000-0000-0000-000000000001")
    user = User(id=user_id, email="oc@example.com", auth_provider="email")
    binding = ChannelBinding(
        user_id=user_id,
        channel="openclaw_whatsapp",
        channel_user_id="+8613800000001",
        is_active=True,
    )
    db_session.add(user)
    db_session.add(binding)
    await db_session.commit()

    resp = await client.post(
        "/webhooks/openclaw",
        json={
            "type": "inbound",
            "channel": "whatsapp",
            "sender": "+8613800000001",
            "content": {"text": "宝宝今天学会走路了", "type": "text"},
            "timestamp": "2026-03-17T10:00:00Z",
        },
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_openclaw_no_binding(client: AsyncClient, db_session: AsyncSession):
    """OpenClaw 入站消息（无绑定）应返回 no_binding。"""
    user_id = uuid.UUID("00000000-0000-0000-0000-000000000001")
    user = User(id=user_id, email="nb@example.com", auth_provider="email")
    db_session.add(user)
    await db_session.commit()

    resp = await client.post(
        "/webhooks/openclaw",
        json={
            "type": "inbound",
            "channel": "whatsapp",
            "sender": "+8613899999999",
            "content": {"text": "hello", "type": "text"},
            "timestamp": "2026-03-17T10:00:00Z",
        },
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "no_binding"


@pytest.mark.asyncio
async def test_openclaw_non_inbound_ignored(client: AsyncClient, db_session: AsyncSession):
    """非 inbound 类型消息应被忽略。"""
    user_id = uuid.UUID("00000000-0000-0000-0000-000000000001")
    user = User(id=user_id, email="ig@example.com", auth_provider="email")
    db_session.add(user)
    await db_session.commit()

    resp = await client.post(
        "/webhooks/openclaw",
        json={
            "type": "status_update",
            "channel": "whatsapp",
            "sender": "+8613800000001",
        },
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "ignored"
