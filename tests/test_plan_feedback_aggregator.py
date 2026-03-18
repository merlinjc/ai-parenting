"""微计划反馈聚合器单元测试。

测试 plan_feedback_aggregator 的核心聚合逻辑和渲染函数。
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta, timezone

import pytest

from ai_parenting.backend.services.plan_feedback_aggregator import (
    DayCompletionSummary,
    PlanFeedbackContext,
    render_feedback_context_text,
)


# ---------------------------------------------------------------------------
# PlanFeedbackContext 模型测试
# ---------------------------------------------------------------------------


class TestPlanFeedbackContext:
    """PlanFeedbackContext Pydantic 模型测试。"""

    def test_default_empty_context(self):
        """空上下文（无上轮计划）应使用默认值。"""
        ctx = PlanFeedbackContext()
        assert ctx.has_previous_plan is False
        assert ctx.completion_rate == 0.0
        assert ctx.day_completions == []
        assert ctx.feedback_decision is None
        assert ctx.trend_keywords == []

    def test_full_context(self):
        """完整上下文应正确构建。"""
        ctx = PlanFeedbackContext(
            has_previous_plan=True,
            previous_plan_title="选择表达周计划",
            previous_focus_theme="language",
            completion_rate=0.71,
            day_completions=[
                DayCompletionSummary(day_number=i, status="executed", main_exercise_title=f"Day{i}")
                for i in range(1, 8)
            ],
            executed_days=5,
            partial_days=1,
            skipped_days=1,
            feedback_decision="continue",
            feedback_summary="孩子在选择表达上有明显进步",
            positive_changes_count=2,
            opportunities_count=1,
            record_count_this_week=12,
            trend_keywords=["选择", "表达", "等待"],
            most_frequent_scenes=["点心时间", "选玩具"],
            risk_level_changed=False,
            previous_risk_level="attention",
            current_risk_level="attention",
        )
        assert ctx.has_previous_plan is True
        assert ctx.completion_rate == 0.71
        assert len(ctx.day_completions) == 7
        assert ctx.executed_days == 5

    def test_completion_rate_bounds(self):
        """completion_rate 必须在 0.0-1.0 范围内。"""
        ctx = PlanFeedbackContext(completion_rate=0.0)
        assert ctx.completion_rate == 0.0

        ctx = PlanFeedbackContext(completion_rate=1.0)
        assert ctx.completion_rate == 1.0

        with pytest.raises(Exception):
            PlanFeedbackContext(completion_rate=1.5)

        with pytest.raises(Exception):
            PlanFeedbackContext(completion_rate=-0.1)


# ---------------------------------------------------------------------------
# render_feedback_context_text 测试
# ---------------------------------------------------------------------------


class TestRenderFeedbackContextText:
    """反馈上下文文本渲染测试。"""

    @pytest.mark.asyncio
    async def test_empty_context_returns_empty(self):
        """无上轮计划时返回空字符串。"""
        ctx = PlanFeedbackContext()
        result = await render_feedback_context_text(ctx)
        assert result == ""

    @pytest.mark.asyncio
    async def test_basic_context_renders(self):
        """基本上下文应渲染为可读文本。"""
        ctx = PlanFeedbackContext(
            has_previous_plan=True,
            previous_plan_title="选择表达周计划",
            previous_focus_theme="language",
            completion_rate=0.71,
            executed_days=5,
            partial_days=1,
            skipped_days=1,
        )
        result = await render_feedback_context_text(ctx)
        assert "上周计划执行反馈" in result
        assert "选择表达周计划" in result
        assert "71%" in result

    @pytest.mark.asyncio
    async def test_continue_decision_renders(self):
        """continue 决策应生成保持焦点的调整指令。"""
        ctx = PlanFeedbackContext(
            has_previous_plan=True,
            previous_plan_title="测试",
            previous_focus_theme="language",
            completion_rate=0.8,
            executed_days=6,
            partial_days=0,
            skipped_days=1,
            feedback_decision="continue",
        )
        result = await render_feedback_context_text(ctx)
        assert "继续同焦点巩固" in result
        assert "保持同一焦点" in result

    @pytest.mark.asyncio
    async def test_lower_difficulty_decision_renders(self):
        """lower_difficulty 决策应生成降低难度的指令。"""
        ctx = PlanFeedbackContext(
            has_previous_plan=True,
            previous_plan_title="测试",
            previous_focus_theme="emotion",
            completion_rate=0.3,
            executed_days=2,
            partial_days=1,
            skipped_days=4,
            feedback_decision="lower_difficulty",
        )
        result = await render_feedback_context_text(ctx)
        assert "降低难度" in result
        assert "减少互动回合数" in result

    @pytest.mark.asyncio
    async def test_change_focus_decision_renders(self):
        """change_focus 决策应生成切换焦点的指令。"""
        ctx = PlanFeedbackContext(
            has_previous_plan=True,
            previous_plan_title="测试",
            previous_focus_theme="social",
            completion_rate=0.5,
            executed_days=3,
            partial_days=1,
            skipped_days=3,
            feedback_decision="change_focus",
        )
        result = await render_feedback_context_text(ctx)
        assert "切换到新的焦点主题" in result

    @pytest.mark.asyncio
    async def test_low_completion_rate_adds_warning(self):
        """低完成率应添加额外降低任务量的指令。"""
        ctx = PlanFeedbackContext(
            has_previous_plan=True,
            previous_plan_title="测试",
            previous_focus_theme="language",
            completion_rate=0.2,
            executed_days=1,
            partial_days=1,
            skipped_days=5,
        )
        result = await render_feedback_context_text(ctx)
        assert "完成率偏低" in result

    @pytest.mark.asyncio
    async def test_risk_change_renders_warning(self):
        """风险变化应渲染警告。"""
        ctx = PlanFeedbackContext(
            has_previous_plan=True,
            previous_plan_title="测试",
            previous_focus_theme="language",
            completion_rate=0.5,
            executed_days=3,
            partial_days=1,
            skipped_days=3,
            risk_level_changed=True,
            previous_risk_level="normal",
            current_risk_level="attention",
        )
        result = await render_feedback_context_text(ctx)
        assert "风险层级变化" in result
        assert "normal → attention" in result

    @pytest.mark.asyncio
    async def test_trend_keywords_rendered(self):
        """趋势关键词应被渲染。"""
        ctx = PlanFeedbackContext(
            has_previous_plan=True,
            previous_plan_title="测试",
            previous_focus_theme="language",
            completion_rate=0.5,
            executed_days=3,
            partial_days=1,
            skipped_days=3,
            record_count_this_week=8,
            trend_keywords=["选择", "表达", "等待", "回应"],
            most_frequent_scenes=["点心时间", "选玩具"],
        )
        result = await render_feedback_context_text(ctx)
        assert "选择" in result
        assert "点心时间" in result
        assert "8 条观察记录" in result
