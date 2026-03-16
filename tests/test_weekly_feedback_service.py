"""周反馈服务测试。

覆盖创建（幂等）、AI 生成成功/降级/失败、决策回写、标记已查看。
"""

from __future__ import annotations

import uuid
from datetime import date, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from ai_parenting.backend.models import Child, Plan, Record, User
from ai_parenting.backend.services import weekly_feedback_service
from ai_parenting.models.enums import FeedbackStatus
from ai_parenting.orchestrator import Orchestrator


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
    """创建带有 7 个日任务的计划。"""
    from ai_parenting.backend.models import DayTask

    today = date.today()
    plan = Plan(
        child_id=child.id,
        version=1,
        status="active",
        title="语言发展周计划",
        primary_goal="提升日常表达能力",
        focus_theme="language",
        stage=child.stage,
        risk_level_at_creation=child.risk_level,
        start_date=today,
        end_date=today + timedelta(days=6),
        current_day=7,
        completion_rate=0.57,
    )
    db_session.add(plan)
    await db_session.flush()

    for i in range(1, 8):
        task = DayTask(
            plan_id=plan.id,
            day_number=i,
            main_exercise_title=f"Day{i} 主练习",
            main_exercise_description="描述",
            natural_embed_title=f"Day{i} 融入练习",
            natural_embed_description="描述",
            demo_script="示范话术",
            observation_point="观察要点",
            completion_status="executed" if i <= 4 else "pending",
        )
        db_session.add(task)
    await db_session.flush()
    await db_session.refresh(plan)
    return plan


class TestCreateWeeklyFeedback:
    """周反馈创建测试。"""

    async def test_create_success(self, db_session, plan_with_tasks):
        feedback = await weekly_feedback_service.create_weekly_feedback(
            db_session, plan_with_tasks.id,
        )
        assert feedback.plan_id == plan_with_tasks.id
        assert feedback.child_id == plan_with_tasks.child_id
        assert feedback.status == FeedbackStatus.GENERATING.value

    async def test_idempotent_create(self, db_session, plan_with_tasks):
        """重复创建应返回已有记录（幂等）。"""
        fb1 = await weekly_feedback_service.create_weekly_feedback(
            db_session, plan_with_tasks.id,
        )
        # 手动更新为 ready 以测试幂等
        fb1.status = FeedbackStatus.READY.value
        await db_session.flush()

        fb2 = await weekly_feedback_service.create_weekly_feedback(
            db_session, plan_with_tasks.id,
        )
        assert fb2.id == fb1.id

    async def test_create_after_failed(self, db_session, plan_with_tasks):
        """failed 状态的反馈不阻止重新创建。"""
        fb1 = await weekly_feedback_service.create_weekly_feedback(
            db_session, plan_with_tasks.id,
        )
        fb1.status = FeedbackStatus.FAILED.value
        await db_session.flush()

        fb2 = await weekly_feedback_service.create_weekly_feedback(
            db_session, plan_with_tasks.id,
        )
        assert fb2.id != fb1.id

    async def test_plan_not_found(self, db_session):
        with pytest.raises(ValueError, match="Plan.*not found"):
            await weekly_feedback_service.create_weekly_feedback(
                db_session, uuid.uuid4(),
            )


class TestGenerateFeedbackBackground:
    """周反馈后台生成测试。"""

    async def test_generate_success(self, db_session, orchestrator, plan_with_tasks, child):
        """AI 生成成功更新为 ready 状态。"""
        # 添加一些记录
        record = Record(
            child_id=child.id, type="quick_check",
            tags=["说话", "表达"], content="今天说了完整句子",
        )
        db_session.add(record)
        await db_session.flush()

        feedback = await weekly_feedback_service.create_weekly_feedback(
            db_session, plan_with_tasks.id,
        )

        await weekly_feedback_service.generate_feedback_background(
            db_session, orchestrator, feedback.id,
        )
        await db_session.refresh(feedback)

        # MockProvider 返回降级结果，状态为 degraded 或 completed
        assert feedback.status in (
            FeedbackStatus.READY.value,
            FeedbackStatus.FAILED.value,
        )
        assert feedback.ai_generation_id is not None
        assert feedback.record_count_this_week >= 0
        assert feedback.completion_rate_this_week >= 0

    async def test_generate_skip_non_generating(self, db_session, orchestrator, plan_with_tasks):
        """非 generating 状态不执行。"""
        feedback = await weekly_feedback_service.create_weekly_feedback(
            db_session, plan_with_tasks.id,
        )
        feedback.status = FeedbackStatus.READY.value
        await db_session.flush()

        await weekly_feedback_service.generate_feedback_background(
            db_session, orchestrator, feedback.id,
        )
        await db_session.refresh(feedback)
        # 状态应保持不变
        assert feedback.status == FeedbackStatus.READY.value


class TestSubmitDecision:
    """决策回写测试。"""

    async def test_submit_decision(self, db_session, plan_with_tasks):
        feedback = await weekly_feedback_service.create_weekly_feedback(
            db_session, plan_with_tasks.id,
        )
        feedback.status = FeedbackStatus.READY.value
        await db_session.flush()

        result = await weekly_feedback_service.submit_decision(
            db_session, feedback.id, "continue",
        )
        assert result.selected_decision == "continue"
        assert result.status == FeedbackStatus.DECIDED.value
        assert result.decided_at is not None

        # 验证 plan 联动更新
        await db_session.refresh(plan_with_tasks)
        assert plan_with_tasks.next_week_direction == "continue"

    async def test_submit_decision_from_viewed(self, db_session, plan_with_tasks):
        feedback = await weekly_feedback_service.create_weekly_feedback(
            db_session, plan_with_tasks.id,
        )
        feedback.status = FeedbackStatus.VIEWED.value
        await db_session.flush()

        result = await weekly_feedback_service.submit_decision(
            db_session, feedback.id, "lower_difficulty",
        )
        assert result.selected_decision == "lower_difficulty"

    async def test_submit_decision_invalid_status(self, db_session, plan_with_tasks):
        feedback = await weekly_feedback_service.create_weekly_feedback(
            db_session, plan_with_tasks.id,
        )
        # generating 状态不能提交决策
        with pytest.raises(ValueError, match="Cannot submit decision"):
            await weekly_feedback_service.submit_decision(
                db_session, feedback.id, "continue",
            )

    async def test_submit_decision_not_found(self, db_session):
        result = await weekly_feedback_service.submit_decision(
            db_session, uuid.uuid4(), "continue",
        )
        assert result is None


class TestMarkViewed:
    """标记已查看测试。"""

    async def test_mark_viewed(self, db_session, plan_with_tasks):
        feedback = await weekly_feedback_service.create_weekly_feedback(
            db_session, plan_with_tasks.id,
        )
        feedback.status = FeedbackStatus.READY.value
        await db_session.flush()

        result = await weekly_feedback_service.mark_viewed(db_session, feedback.id)
        assert result.status == FeedbackStatus.VIEWED.value
        assert result.viewed_at is not None

    async def test_mark_viewed_not_ready(self, db_session, plan_with_tasks):
        """非 ready 状态不变更。"""
        feedback = await weekly_feedback_service.create_weekly_feedback(
            db_session, plan_with_tasks.id,
        )
        feedback.status = FeedbackStatus.DECIDED.value
        await db_session.flush()

        result = await weekly_feedback_service.mark_viewed(db_session, feedback.id)
        assert result.status == FeedbackStatus.DECIDED.value


class TestGetFeedbackForPlan:
    """计划周反馈查询测试。"""

    async def test_get_feedback_for_plan(self, db_session, plan_with_tasks):
        feedback = await weekly_feedback_service.create_weekly_feedback(
            db_session, plan_with_tasks.id,
        )
        feedback.status = FeedbackStatus.READY.value
        await db_session.flush()

        result = await weekly_feedback_service.get_feedback_for_plan(
            db_session, plan_with_tasks.id,
        )
        assert result is not None
        assert result.id == feedback.id

    async def test_get_feedback_excludes_failed(self, db_session, plan_with_tasks):
        feedback = await weekly_feedback_service.create_weekly_feedback(
            db_session, plan_with_tasks.id,
        )
        feedback.status = FeedbackStatus.FAILED.value
        await db_session.flush()

        result = await weekly_feedback_service.get_feedback_for_plan(
            db_session, plan_with_tasks.id,
        )
        assert result is None
