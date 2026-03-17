"""渠道管理 API 集成测试。

覆盖端点：
- GET    /api/v1/channels              — 获取绑定列表
- POST   /api/v1/channels/bind         — 绑定渠道
- DELETE /api/v1/channels/{binding_id}  — 解绑渠道
- GET    /api/v1/channels/preferences  — 获取偏好
- PUT    /api/v1/channels/preferences  — 更新偏好
"""

from __future__ import annotations

import uuid

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from ai_parenting.backend.models import User


# ---------------------------------------------------------------------------
# Test Helpers
# ---------------------------------------------------------------------------


async def _create_test_user(db: AsyncSession) -> uuid.UUID:
    """创建测试用户并返回 user_id。"""
    user_id = uuid.UUID("00000000-0000-0000-0000-000000000001")
    user = User(
        id=user_id,
        email="test@example.com",
        auth_provider="email",
        display_name="Test User",
    )
    db.add(user)
    await db.commit()
    return user_id


# ---------------------------------------------------------------------------
# 绑定渠道测试
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_bind_channel_success(client: AsyncClient, db_session: AsyncSession):
    """绑定一个新渠道应返回 201。"""
    await _create_test_user(db_session)

    resp = await client.post(
        "/api/v1/channels/bind",
        json={
            "channel": "wechat",
            "channel_user_id": "o_test_openid_123",
            "display_label": "测试微信号",
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["channel"] == "wechat"
    assert data["channel_user_id"] == "o_test_openid_123"
    assert data["is_active"] is True


@pytest.mark.asyncio
async def test_bind_channel_invalid_type(client: AsyncClient, db_session: AsyncSession):
    """绑定无效渠道类型应返回 422。"""
    await _create_test_user(db_session)

    resp = await client.post(
        "/api/v1/channels/bind",
        json={
            "channel": "email",  # 无效类型
            "channel_user_id": "test@example.com",
        },
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_list_bindings_empty(client: AsyncClient, db_session: AsyncSession):
    """没有绑定时返回空列表。"""
    await _create_test_user(db_session)

    resp = await client.get("/api/v1/channels")
    assert resp.status_code == 200
    data = resp.json()
    assert data["bindings"] == []


@pytest.mark.asyncio
async def test_list_bindings_after_bind(client: AsyncClient, db_session: AsyncSession):
    """绑定后列表应包含该绑定。"""
    await _create_test_user(db_session)

    # 先绑定
    await client.post(
        "/api/v1/channels/bind",
        json={"channel": "apns", "channel_user_id": "device_token_abc"},
    )

    # 再列表
    resp = await client.get("/api/v1/channels")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["bindings"]) == 1
    assert data["bindings"][0]["channel"] == "apns"


@pytest.mark.asyncio
async def test_unbind_channel(client: AsyncClient, db_session: AsyncSession):
    """解绑应返回 204，之后列表为空。"""
    await _create_test_user(db_session)

    # 绑定
    bind_resp = await client.post(
        "/api/v1/channels/bind",
        json={"channel": "wechat", "channel_user_id": "openid_test"},
    )
    binding_id = bind_resp.json()["id"]

    # 解绑
    resp = await client.delete(f"/api/v1/channels/{binding_id}")
    assert resp.status_code == 204

    # 列表应为空（软删除）
    list_resp = await client.get("/api/v1/channels")
    assert len(list_resp.json()["bindings"]) == 0


@pytest.mark.asyncio
async def test_unbind_nonexistent(client: AsyncClient, db_session: AsyncSession):
    """解绑不存在的绑定应返回 404。"""
    await _create_test_user(db_session)

    fake_id = str(uuid.uuid4())
    resp = await client.delete(f"/api/v1/channels/{fake_id}")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# 渠道偏好测试
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_preferences_default(client: AsyncClient, db_session: AsyncSession):
    """首次获取偏好应返回默认值。"""
    await _create_test_user(db_session)

    resp = await client.get("/api/v1/channels/preferences")
    assert resp.status_code == 200
    data = resp.json()
    assert data["quiet_start_hour"] == 22
    assert data["quiet_end_hour"] == 8
    assert data["max_daily_pushes"] == 5


@pytest.mark.asyncio
async def test_update_preferences(client: AsyncClient, db_session: AsyncSession):
    """更新偏好应返回新值。"""
    await _create_test_user(db_session)

    resp = await client.put(
        "/api/v1/channels/preferences",
        json={
            "channel_priority": ["wechat", "apns"],
            "quiet_start_hour": 23,
            "quiet_end_hour": 7,
            "max_daily_pushes": 3,
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["channel_priority"] == ["wechat", "apns"]
    assert data["quiet_start_hour"] == 23
    assert data["max_daily_pushes"] == 3


@pytest.mark.asyncio
async def test_update_preferences_invalid_channel(client: AsyncClient, db_session: AsyncSession):
    """更新偏好时传入无效渠道应返回 422。"""
    await _create_test_user(db_session)

    resp = await client.put(
        "/api/v1/channels/preferences",
        json={"channel_priority": ["sms"]},  # 无效
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_update_preferences_duplicate_channel(client: AsyncClient, db_session: AsyncSession):
    """更新偏好时传入重复渠道应返回 422。"""
    await _create_test_user(db_session)

    resp = await client.put(
        "/api/v1/channels/preferences",
        json={"channel_priority": ["apns", "apns"]},  # 重复
    )
    assert resp.status_code == 422
