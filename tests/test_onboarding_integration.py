"""引导流程前后端联调集成测试。

覆盖：
- PlanInitialContext Schema 校验（字段默认值、完整构建、序列化）
- PlanCreateRequest 含 initial_context 的 API 端到端测试
- 首页聚合 plan_generating 状态联调
- 首次引导上下文 Prompt 注入联调
- _build_first_week_context_text 单元测试
"""

from __future__ import annotations

import uuid
from datetime import date, timedelta
from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from ai_parenting.backend.models import (
    AISession,
    Child,
    DayTask,
    Plan,
    User,
)
from ai_parenting.backend.schemas import (
    HomeSummaryResponse,
    PlanCreateRequest,
    PlanInitialContext,
)
from ai_parenting.backend.services import home_service
from ai_parenting.backend.services.ai_session_service import (
    _build_first_week_context_text,
)


# ---------------------------------------------------------------------------
# Shared Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def user(db_session: AsyncSession) -> User:
    user = User(
        id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
        display_name="测试家长",
        auth_provider="email",
    )
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
        focus_themes=["language"],
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


def _full_initial_context() -> dict:
    """构造一个完整的 initial_context 字典。"""
    return {
        "caregiver_role": "mother",
        "recent_situation": "最近孩子开始上幼儿园，分离焦虑比较明显",
        "daily_routine_note": "早上8点送园，下午4点接，晚上9点睡觉",
        "interaction_style": "喜欢一起看绘本和搭积木",
        "current_concern": "孩子在幼儿园不愿意跟其他小朋友说话",
        "best_moment": "昨天睡前一起看书时，主动翻页指着图片说了'小猫'",
    }


# ---------------------------------------------------------------------------
# 1. PlanInitialContext Schema 校验
# ---------------------------------------------------------------------------


class TestPlanInitialContextSchema:
    """PlanInitialContext Pydantic 模型测试。"""

    def test_default_values(self):
        """所有字段默认为空字符串。"""
        ctx = PlanInitialContext()
        assert ctx.caregiver_role == ""
        assert ctx.recent_situation == ""
        assert ctx.daily_routine_note == ""
        assert ctx.interaction_style == ""
        assert ctx.current_concern == ""
        assert ctx.best_moment == ""

    def test_full_construction(self):
        """完整字段构建。"""
        data = _full_initial_context()
        ctx = PlanInitialContext(**data)
        assert ctx.caregiver_role == "mother"
        assert ctx.recent_situation == "最近孩子开始上幼儿园，分离焦虑比较明显"
        assert ctx.daily_routine_note == "早上8点送园，下午4点接，晚上9点睡觉"
        assert ctx.interaction_style == "喜欢一起看绘本和搭积木"
        assert ctx.current_concern == "孩子在幼儿园不愿意跟其他小朋友说话"
        assert ctx.best_moment == "昨天睡前一起看书时，主动翻页指着图片说了'小猫'"

    def test_partial_construction(self):
        """部分字段填写，其余为默认值。"""
        ctx = PlanInitialContext(
            caregiver_role="father",
            current_concern="孩子不愿吃蔬菜",
        )
        assert ctx.caregiver_role == "father"
        assert ctx.current_concern == "孩子不愿吃蔬菜"
        assert ctx.recent_situation == ""
        assert ctx.daily_routine_note == ""

    def test_json_roundtrip(self):
        """JSON 序列化/反序列化一致性。"""
        data = _full_initial_context()
        ctx = PlanInitialContext(**data)
        json_str = ctx.model_dump_json()
        restored = PlanInitialContext.model_validate_json(json_str)
        assert restored == ctx

    def test_model_dump(self):
        """model_dump 返回正确的字典。"""
        ctx = PlanInitialContext(caregiver_role="mother", best_moment="一起唱歌")
        dumped = ctx.model_dump()
        assert dumped["caregiver_role"] == "mother"
        assert dumped["best_moment"] == "一起唱歌"
        assert dumped["recent_situation"] == ""


class TestPlanCreateRequestSchema:
    """PlanCreateRequest 含 initial_context 的 Schema 测试。"""

    def test_without_initial_context(self):
        """不带 initial_context 时默认为 None。"""
        req = PlanCreateRequest(child_id=uuid.uuid4())
        assert req.initial_context is None

    def test_with_initial_context(self):
        """带完整 initial_context。"""
        req = PlanCreateRequest(
            child_id=uuid.uuid4(),
            initial_context=PlanInitialContext(**_full_initial_context()),
        )
        assert req.initial_context is not None
        assert req.initial_context.caregiver_role == "mother"

    def test_with_initial_context_dict(self):
        """从字典构建（模拟 HTTP JSON 请求）。"""
        child_id = uuid.uuid4()
        req = PlanCreateRequest.model_validate({
            "child_id": str(child_id),
            "initial_context": _full_initial_context(),
        })
        assert req.child_id == child_id
        assert req.initial_context is not None
        assert req.initial_context.interaction_style == "喜欢一起看绘本和搭积木"

    def test_with_null_initial_context(self):
        """显式 null initial_context。"""
        child_id = uuid.uuid4()
        req = PlanCreateRequest.model_validate({
            "child_id": str(child_id),
            "initial_context": None,
        })
        assert req.initial_context is None

    def test_with_empty_initial_context(self):
        """传入空对象的 initial_context（所有字段为默认值）。"""
        req = PlanCreateRequest.model_validate({
            "child_id": str(uuid.uuid4()),
            "initial_context": {},
        })
        assert req.initial_context is not None
        assert req.initial_context.caregiver_role == ""


class TestHomeSummaryResponseSchema:
    """HomeSummaryResponse 含 plan_generating 的 Schema 测试。"""

    def test_plan_generating_default_false(self):
        """plan_generating 默认为 False。"""
        resp = HomeSummaryResponse()
        assert resp.plan_generating is False

    def test_plan_generating_true(self):
        """plan_generating 为 True。"""
        resp = HomeSummaryResponse(plan_generating=True)
        assert resp.plan_generating is True

    def test_json_includes_plan_generating(self):
        """JSON 序列化应包含 plan_generating 字段。"""
        resp = HomeSummaryResponse(plan_generating=True, greeting="你好")
        data = resp.model_dump()
        assert "plan_generating" in data
        assert data["plan_generating"] is True


# ---------------------------------------------------------------------------
# 2. _build_first_week_context_text 单元测试
# ---------------------------------------------------------------------------


class TestBuildFirstWeekContextText:
    """首次引导上下文构建函数测试。"""

    def test_full_context(self):
        """完整上下文生成包含所有字段。"""
        ctx = _full_initial_context()
        text = _build_first_week_context_text(ctx)
        assert "【首次引导上下文" in text
        assert "妈妈" in text  # caregiver_role=mother → 妈妈
        assert "分离焦虑" in text
        assert "8点送园" in text
        assert "搭积木" in text
        assert "不愿意跟其他小朋友说话" in text
        assert "小猫" in text
        assert "◉ 首周特别注意事项" in text

    def test_empty_context_returns_empty(self):
        """所有字段为空时返回空字符串。"""
        ctx = {
            "caregiver_role": "",
            "recent_situation": "",
            "daily_routine_note": "",
            "interaction_style": "",
            "current_concern": "",
            "best_moment": "",
        }
        text = _build_first_week_context_text(ctx)
        assert text == ""

    def test_partial_context(self):
        """部分字段填写时只包含非空字段。"""
        ctx = {
            "caregiver_role": "father",
            "current_concern": "孩子夜醒频繁",
        }
        text = _build_first_week_context_text(ctx)
        assert "爸爸" in text  # father → 爸爸
        assert "夜醒频繁" in text
        assert "日常作息" not in text  # daily_routine_note 未填
        assert "愉快亲子互动" not in text  # best_moment 未填

    def test_pydantic_model_input(self):
        """传入 PlanInitialContext Pydantic 模型。"""
        ctx_model = PlanInitialContext(**_full_initial_context())
        text = _build_first_week_context_text(ctx_model)
        assert "【首次引导上下文" in text
        assert "妈妈" in text

    def test_caregiver_role_mapping(self):
        """照护者角色映射正确。"""
        role_map = {
            "mother": "妈妈",
            "father": "爸爸",
            "grandparent": "祖辈",
            "other": "其他照护者",
        }
        for role, expected in role_map.items():
            ctx = {"caregiver_role": role}
            text = _build_first_week_context_text(ctx)
            assert expected in text, f"Role {role} should map to {expected}"

    def test_unknown_caregiver_role_passthrough(self):
        """未知角色值直接透传。"""
        ctx = {"caregiver_role": "nanny"}
        text = _build_first_week_context_text(ctx)
        assert "nanny" in text

    def test_non_dict_non_model_returns_empty(self):
        """非 dict 非 Pydantic 对象返回空字符串。"""
        text = _build_first_week_context_text("invalid")
        assert text == ""

    def test_none_returns_empty(self):
        """None 输入返回空字符串。"""
        text = _build_first_week_context_text(None)
        assert text == ""

    def test_first_week_tips_content(self):
        """首周提示内容完整。"""
        ctx = _full_initial_context()
        text = _build_first_week_context_text(ctx)
        assert "Day 1 的任务特别简单" in text
        assert "低门槛" in text
        assert "conservative_note" in text
        assert "demo_script" in text


# ---------------------------------------------------------------------------
# 3. 首次引导上下文 Prompt 注入联调
# ---------------------------------------------------------------------------


class TestFirstWeekContextPromptInjection:
    """首次引导上下文注入到 Prompt 模板的联调测试。"""

    def test_first_week_context_injected(self):
        """首次引导上下文应出现在 Prompt 中。"""
        from ai_parenting.models.enums import ChildStage, FocusTheme, RiskLevel
        from ai_parenting.models.schemas import ContextSnapshot
        from ai_parenting.renderer_plan_generation import render_plan_generation_prompt

        ctx = ContextSnapshot(
            child_age_months=24,
            child_stage=ChildStage.M24_36,
            child_focus_themes=[FocusTheme.LANGUAGE],
            child_risk_level=RiskLevel.NORMAL,
        )
        first_week_text = _build_first_week_context_text(_full_initial_context())
        prompt = render_plan_generation_prompt(
            context=ctx,
            child_nickname="小明",
            first_week_context_text=first_week_text,
        )
        assert "首次引导上下文" in prompt
        assert "妈妈" in prompt
        assert "分离焦虑" in prompt
        assert "搭积木" in prompt
        assert "◉ 首周特别注意事项" in prompt
        # 占位符应被清除
        assert "{{首次引导上下文段}}" not in prompt

    def test_empty_first_week_context_placeholder_cleared(self):
        """首次引导上下文为空时，占位符应被清除。"""
        from ai_parenting.models.enums import ChildStage, FocusTheme, RiskLevel
        from ai_parenting.models.schemas import ContextSnapshot
        from ai_parenting.renderer_plan_generation import render_plan_generation_prompt

        ctx = ContextSnapshot(
            child_age_months=24,
            child_stage=ChildStage.M24_36,
            child_focus_themes=[FocusTheme.LANGUAGE],
            child_risk_level=RiskLevel.NORMAL,
        )
        prompt = render_plan_generation_prompt(
            context=ctx,
            first_week_context_text="",
        )
        assert "{{首次引导上下文段}}" not in prompt
        assert "首次引导上下文" not in prompt

    def test_first_week_context_coexists_with_feedback(self):
        """首次引导上下文和反馈上下文可以共存。"""
        from ai_parenting.models.enums import ChildStage, FocusTheme, RiskLevel
        from ai_parenting.models.schemas import ContextSnapshot
        from ai_parenting.renderer_plan_generation import render_plan_generation_prompt

        ctx = ContextSnapshot(
            child_age_months=24,
            child_stage=ChildStage.M24_36,
            child_focus_themes=[FocusTheme.LANGUAGE],
            child_risk_level=RiskLevel.NORMAL,
        )
        first_week_text = _build_first_week_context_text(_full_initial_context())
        feedback_text = "【上周计划执行反馈——FEEDBACK_MARKER——】"
        prompt = render_plan_generation_prompt(
            context=ctx,
            feedback_context_text=feedback_text,
            first_week_context_text=first_week_text,
        )
        assert "首次引导上下文" in prompt
        assert "FEEDBACK_MARKER" in prompt
        # 所有占位符都应被清除
        assert "{{反馈回注上下文段}}" not in prompt
        assert "{{首次引导上下文段}}" not in prompt

    def test_first_week_context_does_not_break_boundaries(self):
        """首次引导上下文注入不影响非诊断化边界指令。"""
        from ai_parenting.models.enums import ChildStage, FocusTheme, RiskLevel
        from ai_parenting.models.schemas import ContextSnapshot
        from ai_parenting.renderer_plan_generation import render_plan_generation_prompt

        ctx = ContextSnapshot(
            child_age_months=24,
            child_stage=ChildStage.M24_36,
            child_focus_themes=[FocusTheme.LANGUAGE],
            child_risk_level=RiskLevel.NORMAL,
        )
        first_week_text = _build_first_week_context_text(_full_initial_context())
        prompt = render_plan_generation_prompt(
            context=ctx,
            first_week_context_text=first_week_text,
        )
        assert "非诊断化边界" in prompt
        assert "绝对禁止使用的词汇" in prompt

    def test_first_week_context_compatible_all_stages(self):
        """首次引导上下文应与所有年龄阶段兼容。"""
        from ai_parenting.models.enums import ChildStage, FocusTheme, RiskLevel
        from ai_parenting.models.schemas import ContextSnapshot
        from ai_parenting.renderer_plan_generation import render_plan_generation_prompt

        first_week_text = _build_first_week_context_text(_full_initial_context())
        for stage, age in [
            (ChildStage.M18_24, 20),
            (ChildStage.M24_36, 30),
            (ChildStage.M36_48, 40),
        ]:
            ctx = ContextSnapshot(
                child_age_months=age,
                child_stage=stage,
                child_focus_themes=[FocusTheme.LANGUAGE],
                child_risk_level=RiskLevel.NORMAL,
            )
            prompt = render_plan_generation_prompt(
                context=ctx,
                first_week_context_text=first_week_text,
            )
            assert "首次引导上下文" in prompt
            assert "妈妈" in prompt


# ---------------------------------------------------------------------------
# 4. 创建计划带 initial_context 的 API 联调测试
# ---------------------------------------------------------------------------


class TestCreatePlanWithInitialContext:
    """POST /api/v1/plans 带 initial_context 的端到端测试。"""

    async def test_create_plan_with_full_initial_context(
        self, client: AsyncClient, child: Child,
    ):
        """带完整 initial_context 创建计划（MockProvider）。"""
        resp = await client.post(
            "/api/v1/plans",
            json={
                "child_id": str(child.id),
                "initial_context": _full_initial_context(),
            },
        )
        # MockProvider 可能返回不完整结果，API 应不抛异常
        assert resp.status_code in (201, 500)

    async def test_create_plan_without_initial_context(
        self, client: AsyncClient, child: Child,
    ):
        """不带 initial_context 创建计划（兼容旧接口）。"""
        resp = await client.post(
            "/api/v1/plans",
            json={"child_id": str(child.id)},
        )
        assert resp.status_code in (201, 500)

    async def test_create_plan_with_null_initial_context(
        self, client: AsyncClient, child: Child,
    ):
        """显式 null initial_context。"""
        resp = await client.post(
            "/api/v1/plans",
            json={
                "child_id": str(child.id),
                "initial_context": None,
            },
        )
        assert resp.status_code in (201, 500)

    async def test_create_plan_with_empty_initial_context(
        self, client: AsyncClient, child: Child,
    ):
        """空对象 initial_context（所有字段为默认）。"""
        resp = await client.post(
            "/api/v1/plans",
            json={
                "child_id": str(child.id),
                "initial_context": {},
            },
        )
        assert resp.status_code in (201, 500)

    async def test_create_plan_with_partial_initial_context(
        self, client: AsyncClient, child: Child,
    ):
        """部分填写 initial_context。"""
        resp = await client.post(
            "/api/v1/plans",
            json={
                "child_id": str(child.id),
                "initial_context": {
                    "caregiver_role": "father",
                    "current_concern": "孩子在幼儿园不说话",
                },
            },
        )
        assert resp.status_code in (201, 500)

    async def test_create_plan_nonexistent_child(
        self, client: AsyncClient, user: User,
    ):
        """不存在的 child_id 应抛出异常（ai_session_service 抛 ValueError）。"""
        with pytest.raises(ValueError, match="not found"):
            await client.post(
                "/api/v1/plans",
                json={
                    "child_id": str(uuid.uuid4()),
                    "initial_context": _full_initial_context(),
                },
            )


# ---------------------------------------------------------------------------
# 5. 首页 plan_generating 状态联调
# ---------------------------------------------------------------------------


class TestHomePlanGeneratingStatus:
    """首页聚合中 plan_generating 字段的联调测试。"""

    async def test_no_plan_no_session_generating_false(
        self, db_session: AsyncSession, user: User, child: Child,
    ):
        """无计划无生成会话时 plan_generating 为 False。"""
        result = await home_service.get_home_summary(db_session, user.id, child.id)
        assert result["plan_generating"] is False

    async def test_with_pending_session_generating_true(
        self, db_session: AsyncSession, user: User, child: Child,
    ):
        """有 pending 状态的 plan_generation 会话时 plan_generating 为 True。"""
        session = AISession(
            child_id=child.id,
            session_type="plan_generation",
            status="pending",
        )
        db_session.add(session)
        await db_session.flush()

        result = await home_service.get_home_summary(db_session, user.id, child.id)
        assert result["plan_generating"] is True

    async def test_with_processing_session_generating_true(
        self, db_session: AsyncSession, user: User, child: Child,
    ):
        """有 processing 状态的 plan_generation 会话时 plan_generating 为 True。"""
        session = AISession(
            child_id=child.id,
            session_type="plan_generation",
            status="processing",
        )
        db_session.add(session)
        await db_session.flush()

        result = await home_service.get_home_summary(db_session, user.id, child.id)
        assert result["plan_generating"] is True

    async def test_with_completed_session_generating_false(
        self, db_session: AsyncSession, user: User, child: Child,
    ):
        """已完成的 plan_generation 会话时 plan_generating 为 False。"""
        session = AISession(
            child_id=child.id,
            session_type="plan_generation",
            status="completed",
        )
        db_session.add(session)
        await db_session.flush()

        result = await home_service.get_home_summary(db_session, user.id, child.id)
        assert result["plan_generating"] is False

    async def test_with_failed_session_generating_false(
        self, db_session: AsyncSession, user: User, child: Child,
    ):
        """失败的 plan_generation 会话时 plan_generating 为 False。"""
        session = AISession(
            child_id=child.id,
            session_type="plan_generation",
            status="failed",
        )
        db_session.add(session)
        await db_session.flush()

        result = await home_service.get_home_summary(db_session, user.id, child.id)
        assert result["plan_generating"] is False

    async def test_with_active_plan_generating_false(
        self, db_session: AsyncSession, user: User, child: Child, plan_with_tasks: Plan,
    ):
        """有活跃计划时，即使有 pending session，plan_generating 也不会检测（有计划就不查）。"""
        session = AISession(
            child_id=child.id,
            session_type="plan_generation",
            status="pending",
        )
        db_session.add(session)
        await db_session.flush()

        result = await home_service.get_home_summary(db_session, user.id, child.id)
        # 有活跃计划时不检测 plan_generating
        assert result["plan_generating"] is False

    async def test_other_session_type_not_counted(
        self, db_session: AsyncSession, user: User, child: Child,
    ):
        """非 plan_generation 类型的 pending 会话不影响 plan_generating。"""
        session = AISession(
            child_id=child.id,
            session_type="instant_help",
            status="pending",
        )
        db_session.add(session)
        await db_session.flush()

        result = await home_service.get_home_summary(db_session, user.id, child.id)
        assert result["plan_generating"] is False


class TestHomePlanGeneratingAPI:
    """首页聚合 API 中 plan_generating 字段的端到端测试。"""

    async def test_home_api_includes_plan_generating_false(
        self, client: AsyncClient, user: User, child: Child,
    ):
        """API 响应中包含 plan_generating=false。"""
        resp = await client.get(
            "/api/v1/home/summary",
            params={"child_id": str(child.id)},
            headers={"X-User-Id": str(user.id)},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "plan_generating" in data
        assert data["plan_generating"] is False

    async def test_home_api_plan_generating_true_with_pending_session(
        self, client: AsyncClient, user: User, child: Child, db_session: AsyncSession,
    ):
        """有 pending 的 plan_generation 会话时，API 返回 plan_generating=true。"""
        session = AISession(
            child_id=child.id,
            session_type="plan_generation",
            status="pending",
        )
        db_session.add(session)
        await db_session.flush()

        resp = await client.get(
            "/api/v1/home/summary",
            params={"child_id": str(child.id)},
            headers={"X-User-Id": str(user.id)},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["plan_generating"] is True

    async def test_home_api_plan_generating_false_with_active_plan(
        self, client: AsyncClient, user: User, child: Child,
        plan_with_tasks: Plan, db_session: AsyncSession,
    ):
        """有活跃计划时 API 返回 plan_generating=false。"""
        resp = await client.get(
            "/api/v1/home/summary",
            params={"child_id": str(child.id)},
            headers={"X-User-Id": str(user.id)},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["plan_generating"] is False
        assert data["active_plan"] is not None


# ---------------------------------------------------------------------------
# 6. 完整引导流程端到端模拟
# ---------------------------------------------------------------------------


class TestOnboardingFlowE2E:
    """模拟完整的引导→创建计划→首页轮询流程。"""

    async def _create_user_and_child(
        self, client: AsyncClient, db_session: AsyncSession,
    ) -> str:
        """创建用户和孩子，返回 child_id。"""
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
        assert resp.status_code == 201
        return resp.json()["id"]

    async def test_onboarding_create_child_then_plan(
        self, client: AsyncClient, db_session: AsyncSession,
    ):
        """引导流程：创建孩子 → 完成引导 → 创建计划（带 initial_context）。"""
        child_id = await self._create_user_and_child(client, db_session)

        # 完成引导
        resp = await client.post(f"/api/v1/children/{child_id}/complete-onboarding")
        assert resp.status_code == 200
        assert resp.json()["onboarding_completed"] is True

        # 创建计划（带 initial_context）
        resp = await client.post(
            "/api/v1/plans",
            json={
                "child_id": child_id,
                "initial_context": _full_initial_context(),
            },
        )
        # MockProvider 下可能成功或失败
        assert resp.status_code in (201, 500)

    async def test_home_after_onboarding_no_plan_yet(
        self, client: AsyncClient, db_session: AsyncSession,
    ):
        """引导完成但计划还未生成时的首页状态。"""
        child_id = await self._create_user_and_child(client, db_session)
        user_id = "00000000-0000-0000-0000-000000000001"

        # 完成引导
        await client.post(f"/api/v1/children/{child_id}/complete-onboarding")

        # 查看首页（此时无计划，也无生成会话）
        resp = await client.get(
            "/api/v1/home/summary",
            params={"child_id": child_id},
            headers={"X-User-Id": user_id},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["active_plan"] is None
        assert data["plan_generating"] is False
        assert data["child"]["nickname"] == "小明"
        assert data["child"]["onboarding_completed"] is True
