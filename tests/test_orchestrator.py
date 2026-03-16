"""统一编排调度器测试。

覆盖：
- 正常流程（三种 session_type）
- 超时降级
- 结构不合格降级（解析失败 → 重试 → 降级）
- 边界违规 → 替换后返回
- 重试逻辑验证
"""

import asyncio
import json

import pytest

from ai_parenting.models.enums import (
    ChildStage,
    DecisionValue,
    FocusTheme,
    RiskLevel,
    SessionStatus,
    SessionType,
)
from ai_parenting.models.schemas import (
    ContextSnapshot,
    InstantHelpResult,
    PlanGenerationResult,
    WeeklyFeedbackResult,
)
from ai_parenting.orchestrator import Orchestrator, OrchestrateResult
from ai_parenting.providers.mock_provider import MockProvider


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_context(
    stage: ChildStage = ChildStage.M24_36,
    risk: RiskLevel = RiskLevel.NORMAL,
) -> ContextSnapshot:
    return ContextSnapshot(
        child_age_months=26,
        child_stage=stage,
        child_focus_themes=[FocusTheme.LANGUAGE],
        child_risk_level=risk,
        active_plan_id="plan-001",
        active_plan_day=3,
        recent_record_keywords=["指向", "选择表达"],
    )


def _make_instant_help_json() -> str:
    return json.dumps({
        "step_one": {"title": "先稳住节奏", "body": "深呼吸一次。孩子坐不住是常见的。", "example_script": None},
        "step_two": {"title": "给一个小选择", "body": "不催促坐下，给一个跟吃饭相关的选择。", "example_script": "你要用勺子还是叉子？"},
        "step_three": {"title": "留一个退路", "body": "如果走开了，等一两分钟后再邀请一次。", "example_script": "饭还在这里。"},
        "scenario_summary": "吃饭时坐不住",
        "suggest_record": True,
        "suggest_add_focus": False,
        "suggest_consult_prep": False,
        "consult_prep_reason": None,
        "boundary_note": "以上为支持性建议。如持续担心建议咨询。",
    }, ensure_ascii=False)


def _make_plan_generation_json() -> str:
    return json.dumps({
        "title": "这周练习表达选择",
        "primary_goal": "在日常场景中练习表达",
        "focus_theme": "language",
        "priority_scenes": ["点心时间", "选玩具"],
        "day_tasks": [
            {
                "day_number": i,
                "main_exercise_title": f"Day {i} 练习",
                "main_exercise_description": f"Day {i} 练习描述内容",
                "natural_embed_title": f"Day {i} 嵌入",
                "natural_embed_description": f"Day {i} 嵌入描述内容",
                "demo_script": "你要苹果还是香蕉？",
                "observation_point": "观察是否有回应。",
            }
            for i in range(1, 8)
        ],
        "observation_candidates": [
            {"id": f"oc_0{i}", "text": f"候选项{i}", "theme": "language", "default_selected": i <= 2}
            for i in range(1, 6)
        ],
        "weekend_review_prompt": "回想这周哪个场景最容易出现互动。",
        "conservative_note": "如果吃力，先只保留一个场景。",
    }, ensure_ascii=False)


def _make_weekly_feedback_json() -> str:
    return json.dumps({
        "positive_changes": [
            {
                "title": "转场更顺了",
                "description": "本周预告后孩子更快接受。",
                "supporting_evidence": "周三记录提到哭闹减少",
            },
        ],
        "opportunities": [
            {"title": "睡前仍难", "description": "睡前转场仍然困难。"},
        ],
        "summary_text": "这一周在洗澡转场上有值得注意的变化。",
        "decision_options": [
            {"id": "opt_c", "text": "继续", "value": "continue", "rationale": "巩固改善"},
            {"id": "opt_l", "text": "放慢", "value": "lower_difficulty", "rationale": "减少压力"},
            {"id": "opt_f", "text": "换方向", "value": "change_focus", "rationale": "尝试新主题"},
        ],
        "conservative_path_note": "可以先暂停新的练习安排。",
        "referenced_record_ids": ["uuid-001"],
        "referenced_plan_id": "uuid-plan",
    }, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Normal Flow Tests
# ---------------------------------------------------------------------------


class TestNormalFlow:
    @pytest.mark.asyncio
    async def test_instant_help_normal(self):
        provider = MockProvider(response_json=_make_instant_help_json())
        orchestrator = Orchestrator(provider)
        result = await orchestrator.orchestrate(
            session_type=SessionType.INSTANT_HELP,
            context=_make_context(),
            user_scenario="吃饭不坐",
            user_input_text="孩子一直站着",
            child_nickname="小明",
        )
        assert result.status == SessionStatus.COMPLETED
        assert isinstance(result.result, InstantHelpResult)
        assert result.metadata.model_provider == "mock"
        assert result.metadata.boundary_check_passed is True

    @pytest.mark.asyncio
    async def test_plan_generation_normal(self):
        provider = MockProvider(response_json=_make_plan_generation_json())
        orchestrator = Orchestrator(provider)
        result = await orchestrator.orchestrate(
            session_type=SessionType.PLAN_GENERATION,
            context=_make_context(),
            child_nickname="小明",
        )
        assert result.status == SessionStatus.COMPLETED
        assert isinstance(result.result, PlanGenerationResult)
        assert len(result.result.day_tasks) == 7

    @pytest.mark.asyncio
    async def test_weekly_feedback_normal(self):
        provider = MockProvider(response_json=_make_weekly_feedback_json())
        orchestrator = Orchestrator(provider)
        result = await orchestrator.orchestrate(
            session_type=SessionType.WEEKLY_FEEDBACK,
            context=_make_context(),
            child_nickname="小明",
            active_plan_title="练习情绪过渡",
            active_plan_focus_theme="emotion",
            plan_completion_rate="71%",
            record_count_this_week=5,
            day_tasks_summary="已完成5天",
            weekly_records_detail="记录详情",
            active_plan_id="plan-001",
        )
        assert result.status == SessionStatus.COMPLETED
        assert isinstance(result.result, WeeklyFeedbackResult)


# ---------------------------------------------------------------------------
# Timeout Degradation Tests
# ---------------------------------------------------------------------------


class TestTimeoutDegradation:
    @pytest.mark.asyncio
    async def test_instant_help_timeout_degrades(self):
        provider = MockProvider(simulate_timeout=True)
        orchestrator = Orchestrator(provider)
        result = await orchestrator.orchestrate(
            session_type=SessionType.INSTANT_HELP,
            context=_make_context(),
            user_scenario="测试",
            user_input_text="测试",
        )
        assert result.status == SessionStatus.DEGRADED
        assert isinstance(result.result, InstantHelpResult)
        assert result.result.step_one.title == "先稳住自己"  # 降级结果

    @pytest.mark.asyncio
    async def test_plan_generation_timeout_degrades(self):
        provider = MockProvider(simulate_timeout=True)
        orchestrator = Orchestrator(provider)
        result = await orchestrator.orchestrate(
            session_type=SessionType.PLAN_GENERATION,
            context=_make_context(),
        )
        assert result.status == SessionStatus.DEGRADED
        assert isinstance(result.result, PlanGenerationResult)


# ---------------------------------------------------------------------------
# Parse Failure + Retry + Degradation Tests
# ---------------------------------------------------------------------------


class TestParseFailureDegradation:
    @pytest.mark.asyncio
    async def test_invalid_json_degrades_after_retry(self):
        provider = MockProvider(simulate_invalid_json=True)
        orchestrator = Orchestrator(provider)
        result = await orchestrator.orchestrate(
            session_type=SessionType.INSTANT_HELP,
            context=_make_context(),
            user_scenario="测试",
            user_input_text="测试",
        )
        assert result.status == SessionStatus.DEGRADED
        assert provider.call_count == 2  # 首次 + 1 次重试

    @pytest.mark.asyncio
    async def test_retry_succeeds_on_second_attempt(self):
        provider = MockProvider()
        # 第一次返回非法 JSON，第二次返回合法 JSON
        provider.set_responses([
            "invalid json",
            _make_instant_help_json(),
        ])
        orchestrator = Orchestrator(provider)
        result = await orchestrator.orchestrate(
            session_type=SessionType.INSTANT_HELP,
            context=_make_context(),
            user_scenario="测试",
            user_input_text="测试",
        )
        assert result.status == SessionStatus.COMPLETED
        assert isinstance(result.result, InstantHelpResult)
        assert provider.call_count == 2


# ---------------------------------------------------------------------------
# Boundary Violation Tests
# ---------------------------------------------------------------------------


class TestBoundaryViolation:
    @pytest.mark.asyncio
    async def test_boundary_violation_returns_cleaned(self):
        """边界违规 → 替换后返回，状态仍为 COMPLETED。"""
        # 构造一个包含诊断标签的响应
        bad_json = json.dumps({
            "step_one": {"title": "先稳住节奏", "body": "这不像自闭的表现。"},
            "step_two": {"title": "给一个选择", "body": "给孩子选择。"},
            "step_three": {"title": "留退路", "body": "等一等再试。"},
            "scenario_summary": "场景摘要",
            "suggest_record": True,
            "suggest_add_focus": False,
            "suggest_consult_prep": False,
            "consult_prep_reason": None,
            "boundary_note": "以上为支持性建议。",
        }, ensure_ascii=False)
        provider = MockProvider(response_json=bad_json)
        orchestrator = Orchestrator(provider)
        result = await orchestrator.orchestrate(
            session_type=SessionType.INSTANT_HELP,
            context=_make_context(),
            user_scenario="测试",
            user_input_text="测试",
        )
        assert result.status == SessionStatus.COMPLETED
        assert result.metadata.boundary_check_passed is False
        assert "diagnosis_label" in result.metadata.boundary_check_flags
        # 清洁后结果中不应包含诊断标签
        assert isinstance(result.result, InstantHelpResult)
        assert "自闭" not in result.result.step_one.body


# ---------------------------------------------------------------------------
# Metadata Tests
# ---------------------------------------------------------------------------


class TestMetadata:
    @pytest.mark.asyncio
    async def test_metadata_populated(self):
        provider = MockProvider(response_json=_make_instant_help_json())
        orchestrator = Orchestrator(provider)
        result = await orchestrator.orchestrate(
            session_type=SessionType.INSTANT_HELP,
            context=_make_context(),
            user_scenario="测试",
            user_input_text="测试",
        )
        assert result.metadata.prompt_template_version == "tpl_instant_help_v1/1.0.0"
        assert result.metadata.model_provider == "mock"
        assert result.metadata.model_version == "mock-v1"
        assert result.metadata.latency_ms >= 0
        assert result.metadata.generation_timestamp is not None
