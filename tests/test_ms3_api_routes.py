"""MS3 新增 API 集成测试。

覆盖首页聚合、周反馈生命周期、消息 CRUD、推送回流和风险升级端到端。
"""

from __future__ import annotations

import uuid
from datetime import date, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from ai_parenting.backend.models import (
    Child,
    DayTask,
    Message,
    Plan,
    Record,
    User,
    WeeklyFeedback,
)


@pytest.fixture
async def user(db_session: AsyncSession) -> User:
    user = User(display_name="测试家长", auth_provider="email")
    db_session.add(user)
    await db_session.flush()
    return user


@pytest.fixture
async def child(db_session: AsyncSession, user: User) -> Child:
    child = Child(
        user_id=user.id,
        nickname="小明",
        birth_year_month="2024-01",
        age_months=24,
        stage="24_36m",
        risk_level="normal",
    )
    db_session.add(child)
    await db_session.flush()
    return child


@pytest.fixture
async def plan_with_tasks(db_session: AsyncSession, child: Child) -> Plan:
    today = date.today()
    plan = Plan(
        child_id=child.id,
        version=1,
        status="active",
        title="语言发展周计划",
        primary_goal="提升表达能力",
        focus_theme="language",
        stage=child.stage,
        risk_level_at_creation=child.risk_level,
        start_date=today,
        end_date=today + timedelta(days=6),
        current_day=1,
        completion_rate=0.0,
    )
    db_session.add(plan)
    await db_session.flush()

    for i in range(1, 8):
        task = DayTask(
            plan_id=plan.id,
            day_number=i,
            main_exercise_title=f"Day{i} 练习",
            main_exercise_description="描述",
            natural_embed_title=f"Day{i} 融入",
            natural_embed_description="描述",
            demo_script="话术",
            observation_point="观察",
            completion_status="pending",
        )
        db_session.add(task)
    await db_session.flush()
    await db_session.refresh(plan)
    return plan


# ---------------------------------------------------------------------------
# 首页聚合 API
# ---------------------------------------------------------------------------


class TestHomeAPI:
    """首页聚合测试。"""

    async def test_home_summary_basic(self, client: AsyncClient, child: Child, user: User):
        resp = await client.get(
            "/api/v1/home/summary",
            params={"child_id": str(child.id)},
            headers={"X-User-Id": str(user.id)},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["child"]["nickname"] == "小明"
        assert data["unread_count"] == 0

    async def test_home_with_plan(
        self, client: AsyncClient, child: Child, user: User, plan_with_tasks: Plan,
    ):
        resp = await client.get(
            "/api/v1/home/summary",
            params={"child_id": str(child.id)},
            headers={"X-User-Id": str(user.id)},
        )
        data = resp.json()
        assert data["active_plan"] is not None
        assert data["active_plan"]["title"] == "语言发展周计划"
        assert data["today_task"] is not None

    async def test_home_with_unread_messages(
        self, client: AsyncClient, child: Child, user: User, db_session: AsyncSession,
    ):
        # 手动创建消息
        for _ in range(3):
            msg = Message(
                user_id=user.id,
                type="plan_reminder",
                title="测试",
                body="内容",
                summary="摘要",
                read_status="unread",
                push_status="pending",
            )
            db_session.add(msg)
        await db_session.flush()

        resp = await client.get(
            "/api/v1/home/summary",
            params={"child_id": str(child.id)},
            headers={"X-User-Id": str(user.id)},
        )
        data = resp.json()
        assert data["unread_count"] == 3


# ---------------------------------------------------------------------------
# 消息 API
# ---------------------------------------------------------------------------


class TestMessagesAPI:
    """消息路由测试。"""

    async def test_list_empty(self, client: AsyncClient, user: User):
        resp = await client.get(
            "/api/v1/messages",
            headers={"X-User-Id": str(user.id)},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["messages"] == []
        assert data["total_unread"] == 0

    async def test_list_with_messages(
        self, client: AsyncClient, user: User, db_session: AsyncSession,
    ):
        for _ in range(3):
            msg = Message(
                user_id=user.id, type="plan_reminder",
                title="测试", body="内容", summary="摘要",
                read_status="unread", push_status="pending",
            )
            db_session.add(msg)
        await db_session.flush()

        resp = await client.get(
            "/api/v1/messages",
            headers={"X-User-Id": str(user.id)},
        )
        data = resp.json()
        assert len(data["messages"]) == 3
        assert data["total_unread"] == 3

    async def test_get_unread_count(
        self, client: AsyncClient, user: User, db_session: AsyncSession,
    ):
        msg = Message(
            user_id=user.id, type="plan_reminder",
            title="测试", body="内容", summary="摘要",
            read_status="unread", push_status="pending",
        )
        db_session.add(msg)
        await db_session.flush()

        resp = await client.get(
            "/api/v1/messages/unread-count",
            headers={"X-User-Id": str(user.id)},
        )
        data = resp.json()
        assert data["unread_count"] == 1

    async def test_get_message_detail(
        self, client: AsyncClient, user: User, db_session: AsyncSession,
    ):
        msg = Message(
            user_id=user.id, type="risk_alert",
            title="风险提醒", body="内容", summary="摘要",
            read_status="unread", push_status="pending",
        )
        db_session.add(msg)
        await db_session.flush()

        resp = await client.get(f"/api/v1/messages/{msg.id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["type"] == "risk_alert"

    async def test_update_read_status(
        self, client: AsyncClient, user: User, db_session: AsyncSession,
    ):
        msg = Message(
            user_id=user.id, type="plan_reminder",
            title="测试", body="内容", summary="摘要",
            read_status="unread", push_status="pending",
        )
        db_session.add(msg)
        await db_session.flush()

        resp = await client.patch(
            f"/api/v1/messages/{msg.id}",
            json={"read_status": "read"},
        )
        assert resp.status_code == 200
        assert resp.json()["read_status"] == "read"

    async def test_message_clicked(
        self, client: AsyncClient, user: User, db_session: AsyncSession,
    ):
        msg = Message(
            user_id=user.id, type="plan_reminder",
            title="测试", body="内容", summary="摘要",
            read_status="unread", push_status="pending",
        )
        db_session.add(msg)
        await db_session.flush()

        resp = await client.post(f"/api/v1/messages/{msg.id}/clicked")
        assert resp.status_code == 200
        data = resp.json()
        assert data["clicked_at"] is not None
        assert data["read_status"] == "read"

    async def test_message_delivered(
        self, client: AsyncClient, user: User, db_session: AsyncSession,
    ):
        msg = Message(
            user_id=user.id, type="plan_reminder",
            title="测试", body="内容", summary="摘要",
            read_status="unread", push_status="sent",
        )
        db_session.add(msg)
        await db_session.flush()

        resp = await client.post(f"/api/v1/messages/{msg.id}/delivered")
        assert resp.status_code == 200
        data = resp.json()
        assert data["push_status"] == "delivered"
        assert data["push_delivered_at"] is not None

    async def test_message_not_found(self, client: AsyncClient):
        resp = await client.get(f"/api/v1/messages/{uuid.uuid4()}")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# 周反馈 API
# ---------------------------------------------------------------------------


class TestWeeklyFeedbackAPI:
    """周反馈路由测试。"""

    async def test_create_feedback(
        self, client: AsyncClient, plan_with_tasks: Plan,
    ):
        resp = await client.post(
            "/api/v1/weekly-feedbacks",
            json={"plan_id": str(plan_with_tasks.id)},
        )
        assert resp.status_code == 202
        data = resp.json()
        assert data["status"] == "generating"
        assert data["plan_id"] == str(plan_with_tasks.id)

    async def test_get_feedback(
        self, client: AsyncClient, plan_with_tasks: Plan, db_session: AsyncSession,
    ):
        fb = WeeklyFeedback(
            plan_id=plan_with_tasks.id,
            child_id=plan_with_tasks.child_id,
            status="ready",
            summary_text="本周表现很棒",
        )
        db_session.add(fb)
        await db_session.flush()

        resp = await client.get(f"/api/v1/weekly-feedbacks/{fb.id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ready"
        assert data["summary_text"] == "本周表现很棒"

    async def test_feedback_not_found(self, client: AsyncClient):
        resp = await client.get(f"/api/v1/weekly-feedbacks/{uuid.uuid4()}")
        assert resp.status_code == 404

    async def test_mark_viewed(
        self, client: AsyncClient, plan_with_tasks: Plan, db_session: AsyncSession,
    ):
        fb = WeeklyFeedback(
            plan_id=plan_with_tasks.id,
            child_id=plan_with_tasks.child_id,
            status="ready",
        )
        db_session.add(fb)
        await db_session.flush()

        resp = await client.post(f"/api/v1/weekly-feedbacks/{fb.id}/viewed")
        assert resp.status_code == 200
        assert resp.json()["status"] == "viewed"

    async def test_submit_decision(
        self, client: AsyncClient, plan_with_tasks: Plan, db_session: AsyncSession,
    ):
        fb = WeeklyFeedback(
            plan_id=plan_with_tasks.id,
            child_id=plan_with_tasks.child_id,
            status="ready",
        )
        db_session.add(fb)
        await db_session.flush()

        resp = await client.post(
            f"/api/v1/weekly-feedbacks/{fb.id}/decision",
            json={"decision": "continue"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["selected_decision"] == "continue"
        assert data["status"] == "decided"

    async def test_submit_invalid_decision(
        self, client: AsyncClient, plan_with_tasks: Plan, db_session: AsyncSession,
    ):
        fb = WeeklyFeedback(
            plan_id=plan_with_tasks.id,
            child_id=plan_with_tasks.child_id,
            status="ready",
        )
        db_session.add(fb)
        await db_session.flush()

        resp = await client.post(
            f"/api/v1/weekly-feedbacks/{fb.id}/decision",
            json={"decision": "invalid"},
        )
        assert resp.status_code == 422

    async def test_plan_not_found(self, client: AsyncClient):
        resp = await client.post(
            "/api/v1/weekly-feedbacks",
            json={"plan_id": str(uuid.uuid4())},
        )
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# 计划页 weekly_feedback_status 真实查询
# ---------------------------------------------------------------------------


class TestPlanFeedbackStatus:
    """计划页周反馈状态联动测试。"""

    async def test_active_plan_with_feedback(
        self, client: AsyncClient, child: Child, plan_with_tasks: Plan, db_session: AsyncSession,
    ):
        fb = WeeklyFeedback(
            plan_id=plan_with_tasks.id,
            child_id=child.id,
            status="ready",
        )
        db_session.add(fb)
        await db_session.flush()

        resp = await client.get(
            "/api/v1/plans/active",
            params={"child_id": str(child.id)},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["weekly_feedback_status"] == "ready"

    async def test_active_plan_without_feedback(
        self, client: AsyncClient, child: Child, plan_with_tasks: Plan,
    ):
        resp = await client.get(
            "/api/v1/plans/active",
            params={"child_id": str(child.id)},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["weekly_feedback_status"] is None


# ---------------------------------------------------------------------------
# 风险升级端到端
# ---------------------------------------------------------------------------


class TestRiskEscalation:
    """风险升级端到端测试。"""

    async def test_instant_help_triggers_risk_escalation(
        self, client: AsyncClient, child: Child, user: User, db_session: AsyncSession,
    ):
        """即时求助端到端：验证 AI 调用后 risk_level 和消息状态。

        MockProvider 返回的结果中 suggest_consult_prep 默认为 False，
        所以这里主要验证正常流程不触发升级。
        """
        resp = await client.post(
            "/api/v1/ai/instant-help",
            json={
                "child_id": str(child.id),
                "scenario": "孩子不愿意说话",
                "input_text": "最近几天都不愿意开口",
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["session_type"] == "instant_help"

        # 正常情况下 risk_level 不变
        await db_session.refresh(child)
        assert child.risk_level == "normal"

    async def test_risk_escalation_logic(
        self, client: AsyncClient, child: Child, user: User, db_session: AsyncSession,
    ):
        """手动模拟风险升级：验证 child.risk_level 变更和消息创建。"""
        from ai_parenting.backend.models import AISession
        from ai_parenting.backend.services.ai_session_service import _check_risk_escalation

        session = AISession(
            child_id=child.id,
            session_type="instant_help",
            status="completed",
        )
        db_session.add(session)
        await db_session.flush()

        # 模拟 AI 结果中包含 suggest_consult_prep=True
        result_dict = {
            "suggest_consult_prep": True,
            "consult_prep_reason": "语言发展滞后",
        }
        await _check_risk_escalation(db_session, child, session, result_dict)
        await db_session.flush()

        await db_session.refresh(child)
        assert child.risk_level == "consult"

        # 验证自动创建了风险提醒消息
        from ai_parenting.backend.services import message_service
        count = await message_service.get_unread_count(db_session, user.id)
        assert count >= 1

    async def test_risk_already_consult_no_duplicate(
        self, client: AsyncClient, child: Child, db_session: AsyncSession,
    ):
        """已是 consult 级别不重复升级。"""
        from ai_parenting.backend.models import AISession
        from ai_parenting.backend.services.ai_session_service import _check_risk_escalation

        child.risk_level = "consult"
        await db_session.flush()

        session = AISession(
            child_id=child.id,
            session_type="instant_help",
            status="completed",
        )
        db_session.add(session)
        await db_session.flush()

        result_dict = {"suggest_consult_prep": True}
        await _check_risk_escalation(db_session, child, session, result_dict)

        # 不应创建新消息
        from ai_parenting.backend.services import message_service
        count = await message_service.get_unread_count(db_session, child.user_id)
        assert count == 0
