"""首页聚合服务单元测试。

覆盖 home_service.get_home_summary() 的全数据聚合、
无计划/无记录降级场景和未读计数正确性。
"""

from __future__ import annotations

import uuid
from datetime import date, timedelta

import pytest
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
from ai_parenting.backend.services import home_service


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


class TestGetHomeSummary:
    """首页聚合 get_home_summary 测试。"""

    async def test_full_aggregation(
        self, db_session: AsyncSession, user: User, child: Child, plan_with_tasks: Plan,
    ):
        """全数据聚合：child + plan + today_task + records + unread。"""
        # 创建记录
        record = Record(
            child_id=child.id,
            type="text",
            content="今天说了新词",
            tags=["language"],
        )
        db_session.add(record)
        await db_session.flush()

        # 创建未读消息
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

        result = await home_service.get_home_summary(db_session, user.id, child.id)

        assert result["child"] is not None
        assert result["child"].nickname == "小明"
        assert result["active_plan"] is not None
        assert result["active_plan"].title == "语言发展周计划"
        assert result["today_task"] is not None
        assert result["today_task"].day_number == 1
        assert len(result["recent_records"]) == 1
        assert result["unread_count"] == 1

    async def test_no_plan_degrades_gracefully(
        self, db_session: AsyncSession, user: User, child: Child,
    ):
        """无活跃计划时，plan 和 today_task 为 None。"""
        result = await home_service.get_home_summary(db_session, user.id, child.id)

        assert result["child"] is not None
        assert result["active_plan"] is None
        assert result["today_task"] is None
        assert result["weekly_feedback_status"] is None
        assert result["weekly_feedback_id"] is None

    async def test_no_records_returns_empty_list(
        self, db_session: AsyncSession, user: User, child: Child,
    ):
        """无记录时 recent_records 为空列表。"""
        result = await home_service.get_home_summary(db_session, user.id, child.id)
        assert result["recent_records"] == []

    async def test_unread_count_zero_when_no_messages(
        self, db_session: AsyncSession, user: User, child: Child,
    ):
        """无消息时 unread_count 为 0。"""
        result = await home_service.get_home_summary(db_session, user.id, child.id)
        assert result["unread_count"] == 0

    async def test_unread_count_accuracy(
        self, db_session: AsyncSession, user: User, child: Child,
    ):
        """多条消息（含已读和未读）时 unread_count 只统计未读。"""
        for i in range(3):
            msg = Message(
                user_id=user.id,
                type="system",
                title=f"消息{i}",
                body="内容",
                summary="摘要",
                read_status="unread" if i < 2 else "read",
                push_status="pending",
            )
            db_session.add(msg)
        await db_session.flush()

        result = await home_service.get_home_summary(db_session, user.id, child.id)
        assert result["unread_count"] == 2

    async def test_weekly_feedback_status_included(
        self, db_session: AsyncSession, user: User, child: Child, plan_with_tasks: Plan,
    ):
        """有周反馈时返回 weekly_feedback_status 和 id。"""
        fb = WeeklyFeedback(
            plan_id=plan_with_tasks.id,
            child_id=child.id,
            status="ready",
            summary_text="本周总结",
        )
        db_session.add(fb)
        await db_session.flush()

        result = await home_service.get_home_summary(db_session, user.id, child.id)
        assert result["weekly_feedback_status"] == "ready"
        assert result["weekly_feedback_id"] == fb.id

    async def test_weekly_feedback_excludes_failed(
        self, db_session: AsyncSession, user: User, child: Child, plan_with_tasks: Plan,
    ):
        """failed 状态的周反馈不展示在首页。"""
        fb = WeeklyFeedback(
            plan_id=plan_with_tasks.id,
            child_id=child.id,
            status="failed",
            error_info="AI generation error",
        )
        db_session.add(fb)
        await db_session.flush()

        result = await home_service.get_home_summary(db_session, user.id, child.id)
        assert result["weekly_feedback_status"] is None
        assert result["weekly_feedback_id"] is None

    async def test_recent_records_limited_to_five(
        self, db_session: AsyncSession, user: User, child: Child,
    ):
        """recent_records 最多返回 5 条。"""
        for i in range(8):
            record = Record(
                child_id=child.id,
                type="text",
                content=f"记录{i}",
            )
            db_session.add(record)
        await db_session.flush()

        result = await home_service.get_home_summary(db_session, user.id, child.id)
        assert len(result["recent_records"]) == 5

    async def test_nonexistent_child(
        self, db_session: AsyncSession, user: User,
    ):
        """不存在的 child_id 时 child 为 None，其余降级。"""
        fake_id = uuid.uuid4()
        result = await home_service.get_home_summary(db_session, user.id, fake_id)
        assert result["child"] is None
        assert result["active_plan"] is None
        assert result["today_task"] is None
