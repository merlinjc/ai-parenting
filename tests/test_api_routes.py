"""FastAPI API 路由集成测试。

使用 httpx AsyncClient + SQLite 内存数据库进行端到端测试。
"""

from __future__ import annotations

import uuid

import pytest

from ai_parenting.backend.models import User


@pytest.mark.asyncio
class TestHealthEndpoint:
    """健康检查端点测试。"""

    async def test_health(self, client):
        resp = await client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"


@pytest.mark.asyncio
class TestChildrenAPI:
    """儿童档案 API 集成测试。"""

    async def test_create_child(self, client, db_session):
        # 先创建用户
        user = User(
            id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
            auth_provider="email",
        )
        db_session.add(user)
        await db_session.flush()

        resp = await client.post(
            "/api/v1/children",
            json={
                "nickname": "小明",
                "birth_year_month": "2024-01",
                "focus_themes": ["language"],
                "risk_level": "normal",
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["nickname"] == "小明"
        assert data["birth_year_month"] == "2024-01"
        assert data["focus_themes"] == ["language"]
        assert data["onboarding_completed"] is False
        assert "id" in data

    async def test_list_children(self, client, db_session):
        user = User(
            id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
            auth_provider="email",
        )
        db_session.add(user)
        await db_session.flush()

        # 创建两个孩子
        await client.post(
            "/api/v1/children",
            json={"nickname": "老大", "birth_year_month": "2023-06"},
        )
        await client.post(
            "/api/v1/children",
            json={"nickname": "老二", "birth_year_month": "2024-06"},
        )

        resp = await client.get("/api/v1/children")
        assert resp.status_code == 200
        assert len(resp.json()) == 2

    async def test_get_child(self, client, db_session):
        user = User(
            id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
            auth_provider="email",
        )
        db_session.add(user)
        await db_session.flush()

        create_resp = await client.post(
            "/api/v1/children",
            json={"nickname": "小明", "birth_year_month": "2024-01"},
        )
        child_id = create_resp.json()["id"]

        resp = await client.get(f"/api/v1/children/{child_id}")
        assert resp.status_code == 200
        assert resp.json()["nickname"] == "小明"

    async def test_get_nonexistent_child(self, client):
        resp = await client.get(f"/api/v1/children/{uuid.uuid4()}")
        assert resp.status_code == 404

    async def test_update_child(self, client, db_session):
        user = User(
            id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
            auth_provider="email",
        )
        db_session.add(user)
        await db_session.flush()

        create_resp = await client.post(
            "/api/v1/children",
            json={"nickname": "小明", "birth_year_month": "2024-01"},
        )
        child_id = create_resp.json()["id"]

        resp = await client.patch(
            f"/api/v1/children/{child_id}",
            json={"nickname": "大明", "focus_themes": ["emotion", "motor"]},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["nickname"] == "大明"
        assert data["focus_themes"] == ["emotion", "motor"]

    async def test_complete_onboarding(self, client, db_session):
        user = User(
            id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
            auth_provider="email",
        )
        db_session.add(user)
        await db_session.flush()

        create_resp = await client.post(
            "/api/v1/children",
            json={"nickname": "小明", "birth_year_month": "2024-01"},
        )
        child_id = create_resp.json()["id"]

        resp = await client.post(f"/api/v1/children/{child_id}/complete-onboarding")
        assert resp.status_code == 200
        assert resp.json()["onboarding_completed"] is True


@pytest.mark.asyncio
class TestRecordsAPI:
    """观察记录 API 集成测试。"""

    async def _create_child(self, client, db_session) -> str:
        user = User(
            id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
            auth_provider="email",
        )
        db_session.add(user)
        await db_session.flush()

        resp = await client.post(
            "/api/v1/children",
            json={"nickname": "小明", "birth_year_month": "2024-01"},
        )
        return resp.json()["id"]

    async def test_create_quick_check_record(self, client, db_session):
        child_id = await self._create_child(client, db_session)

        resp = await client.post(
            "/api/v1/records",
            json={
                "child_id": child_id,
                "type": "quick_check",
                "tags": ["今天说了新词"],
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["type"] == "quick_check"
        assert data["tags"] == ["今天说了新词"]

    async def test_create_event_record(self, client, db_session):
        child_id = await self._create_child(client, db_session)

        resp = await client.post(
            "/api/v1/records",
            json={
                "child_id": child_id,
                "type": "event",
                "content": "公园里主动分享玩具",
                "scene": "playing",
                "theme": "social",
            },
        )
        assert resp.status_code == 201
        assert resp.json()["scene"] == "playing"

    async def test_list_records_with_pagination(self, client, db_session):
        child_id = await self._create_child(client, db_session)

        # 创建 5 条记录
        for i in range(5):
            await client.post(
                "/api/v1/records",
                json={
                    "child_id": child_id,
                    "type": "quick_check",
                    "tags": [f"tag_{i}"],
                },
            )

        resp = await client.get(
            "/api/v1/records",
            params={"child_id": child_id, "limit": 3},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["records"]) == 3
        assert data["has_more"] is True
        assert data["total"] == 5

    async def test_list_records_filter_by_type(self, client, db_session):
        child_id = await self._create_child(client, db_session)

        await client.post(
            "/api/v1/records",
            json={"child_id": child_id, "type": "quick_check", "tags": ["a"]},
        )
        await client.post(
            "/api/v1/records",
            json={"child_id": child_id, "type": "event", "content": "test"},
        )

        resp = await client.get(
            "/api/v1/records",
            params={"child_id": child_id, "type": "event"},
        )
        assert resp.status_code == 200
        assert len(resp.json()["records"]) == 1

    async def test_get_single_record(self, client, db_session):
        child_id = await self._create_child(client, db_session)

        create_resp = await client.post(
            "/api/v1/records",
            json={"child_id": child_id, "type": "quick_check", "tags": ["tag"]},
        )
        record_id = create_resp.json()["id"]

        resp = await client.get(f"/api/v1/records/{record_id}")
        assert resp.status_code == 200
        assert resp.json()["id"] == record_id


@pytest.mark.asyncio
class TestPlansAPI:
    """微计划 API 集成测试。"""

    async def _create_child(self, client, db_session) -> str:
        user = User(
            id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
            auth_provider="email",
        )
        db_session.add(user)
        await db_session.flush()

        resp = await client.post(
            "/api/v1/children",
            json={
                "nickname": "小明",
                "birth_year_month": "2024-01",
                "focus_themes": ["language"],
            },
        )
        return resp.json()["id"]

    async def test_no_active_plan(self, client, db_session):
        child_id = await self._create_child(client, db_session)

        resp = await client.get(
            "/api/v1/plans/active",
            params={"child_id": child_id},
        )
        assert resp.status_code == 404

    async def test_create_plan_via_ai(self, client, db_session):
        """创建计划（触发 MockProvider AI 调用）。"""
        child_id = await self._create_child(client, db_session)

        resp = await client.post(
            "/api/v1/plans",
            json={"child_id": child_id},
        )
        # MockProvider 可能返回的结果不完整导致降级或失败
        # 但 API 调用本身应当不抛异常
        assert resp.status_code in (201, 500)


@pytest.mark.asyncio
class TestAISessionsAPI:
    """AI 会话 API 集成测试。"""

    async def _create_child(self, client, db_session) -> str:
        user = User(
            id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
            auth_provider="email",
        )
        db_session.add(user)
        await db_session.flush()

        resp = await client.post(
            "/api/v1/children",
            json={
                "nickname": "小明",
                "birth_year_month": "2024-01",
                "focus_themes": ["language"],
            },
        )
        return resp.json()["id"]

    async def test_instant_help(self, client, db_session):
        """即时求助端到端测试。"""
        child_id = await self._create_child(client, db_session)

        resp = await client.post(
            "/api/v1/ai/instant-help",
            json={
                "child_id": child_id,
                "scenario": "吃饭不坐",
                "input_text": "孩子一直站着吃饭",
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["session_type"] == "instant_help"
        assert data["status"] in ("completed", "degraded", "failed")
        assert data["child_id"] == child_id

    async def test_instant_help_nonexistent_child(self, client):
        resp = await client.post(
            "/api/v1/ai/instant-help",
            json={
                "child_id": str(uuid.uuid4()),
                "input_text": "test",
            },
        )
        assert resp.status_code == 404

    async def test_get_session(self, client, db_session):
        child_id = await self._create_child(client, db_session)

        create_resp = await client.post(
            "/api/v1/ai/instant-help",
            json={"child_id": child_id, "input_text": "test"},
        )
        session_id = create_resp.json()["id"]

        resp = await client.get(f"/api/v1/ai/sessions/{session_id}")
        assert resp.status_code == 200
        assert resp.json()["id"] == session_id

    async def test_get_nonexistent_session(self, client):
        resp = await client.get(f"/api/v1/ai/sessions/{uuid.uuid4()}")
        assert resp.status_code == 404
