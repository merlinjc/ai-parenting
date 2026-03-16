"""周反馈渲染器集成测试。

覆盖：
- 完整渲染流程
- 9 种阶段 x 风险组合的输出验证
- record_insufficient 条件分支
- 降级结果有效性
- parse_weekly_feedback_result 功能
- 模板版本一致性
- 边界检查（WeeklyFeedbackResult）
"""

import json
from itertools import product

import pytest
from pydantic import ValidationError

from ai_parenting.models.enums import ChildStage, DecisionValue, FocusTheme, RiskLevel
from ai_parenting.models.schemas import ContextSnapshot, WeeklyFeedbackResult
from ai_parenting.renderer_weekly_feedback import (
    check_feedback_boundary,
    get_degraded_feedback_result,
    get_feedback_template_version,
    parse_weekly_feedback_result,
    render_weekly_feedback_prompt,
)
from ai_parenting.templates.weekly_feedback import TEMPLATE_FULL_VERSION


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_context(
    stage: ChildStage = ChildStage.M24_36,
    risk: RiskLevel = RiskLevel.NORMAL,
    age: int = 26,
) -> ContextSnapshot:
    return ContextSnapshot(
        child_age_months=age,
        child_stage=stage,
        child_focus_themes=[FocusTheme.EMOTION],
        child_risk_level=risk,
        active_plan_id="plan-001",
        active_plan_day=7,
        recent_record_keywords=["情绪过渡", "转场"],
    )


def _make_valid_feedback_json() -> str:
    """构造一个合法的 WeeklyFeedbackResult JSON 字符串。"""
    feedback = {
        "positive_changes": [
            {
                "title": "洗澡转场更顺了",
                "description": "本周有三天的记录显示，预告后孩子更快接受。",
                "supporting_evidence": "周三和周五记录都提到'哭闹时间缩短'",
            },
        ],
        "opportunities": [
            {
                "title": "睡前转场仍然比较难",
                "description": "睡前从客厅到卧室的转场仍然是高压场景。",
            },
        ],
        "summary_text": "这一周在洗澡转场上出现了值得注意的变化。",
        "decision_options": [
            {
                "id": "opt_continue",
                "text": "继续本周的预告练习",
                "value": "continue",
                "rationale": "洗澡转场已有改善，再巩固一周",
            },
            {
                "id": "opt_lower",
                "text": "保持方向但放慢节奏",
                "value": "lower_difficulty",
                "rationale": "如果感到执行吃力，可以只保留洗澡场景",
            },
            {
                "id": "opt_change",
                "text": "换一个新的关注方向",
                "value": "change_focus",
                "rationale": "如果觉得情绪过渡不是最紧迫的",
            },
        ],
        "conservative_path_note": "如果这周感觉整体节奏太紧，可以先暂停新的练习安排。",
        "referenced_record_ids": ["uuid-rec-001", "uuid-rec-003"],
        "referenced_plan_id": "uuid-plan-current",
    }
    return json.dumps(feedback, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Basic Render Tests
# ---------------------------------------------------------------------------


class TestRenderWeeklyFeedbackPrompt:
    def test_basic_render(self):
        ctx = _make_context()
        prompt = render_weekly_feedback_prompt(
            context=ctx,
            child_nickname="小明",
            active_plan_title="练习情绪过渡",
            active_plan_focus_theme="emotion",
            plan_completion_rate="71%",
            record_count_this_week=5,
            day_tasks_summary="Day 1-5 已完成，Day 6-7 待完成",
            weekly_records_detail="周三：洗澡预告后哭闹减少。",
            active_plan_id="plan-001",
        )
        assert "周反馈" in prompt
        assert "小明" in prompt
        assert "练习情绪过渡" in prompt
        assert "71%" in prompt

    def test_boundary_directives_injected(self):
        ctx = _make_context()
        prompt = render_weekly_feedback_prompt(context=ctx, record_count_this_week=5)
        assert "非诊断化边界" in prompt
        assert "绝对禁止使用的词汇" in prompt

    def test_output_format_present(self):
        ctx = _make_context()
        prompt = render_weekly_feedback_prompt(context=ctx, record_count_this_week=5)
        assert "positive_changes" in prompt
        assert "decision_options" in prompt
        assert "conservative_path_note" in prompt

    def test_record_insufficient_true(self):
        """record_count < 2 时应出现记录不足提示。"""
        ctx = _make_context()
        prompt = render_weekly_feedback_prompt(
            context=ctx,
            record_count_this_week=1,
        )
        assert "本周记录数少于 2 条" in prompt

    def test_record_insufficient_false(self):
        """record_count >= 2 时不应出现记录不足提示。"""
        ctx = _make_context()
        prompt = render_weekly_feedback_prompt(
            context=ctx,
            record_count_this_week=3,
        )
        assert "本周记录数少于 2 条" not in prompt


# ---------------------------------------------------------------------------
# 9 Stage x Risk Combination Tests
# ---------------------------------------------------------------------------


class TestStageRiskCombinations:
    """验证全部 9 种 阶段 x 风险 组合的 Prompt 输出。"""

    _STAGE_KEYWORDS = {
        ChildStage.M18_24: "18-24 个月阶段",
        ChildStage.M24_36: "24-36 个月阶段",
        ChildStage.M36_48: "36-48 个月阶段",
    }

    _RISK_KEYWORDS = {
        RiskLevel.NORMAL: "正常波动",
        RiskLevel.ATTENTION: "重点关注",
        RiskLevel.CONSULT: "建议咨询",
    }

    _STAGE_AGE_MAP = {
        ChildStage.M18_24: 20,
        ChildStage.M24_36: 30,
        ChildStage.M36_48: 40,
    }

    @pytest.mark.parametrize(
        "stage,risk",
        list(product(ChildStage, RiskLevel)),
        ids=[f"{s.value}-{r.value}" for s, r in product(ChildStage, RiskLevel)],
    )
    def test_combination(self, stage: ChildStage, risk: RiskLevel):
        age = self._STAGE_AGE_MAP[stage]
        ctx = _make_context(stage=stage, risk=risk, age=age)
        prompt = render_weekly_feedback_prompt(
            context=ctx,
            child_nickname="宝宝",
            record_count_this_week=5,
        )

        assert self._STAGE_KEYWORDS[stage] in prompt
        for other_stage, keyword in self._STAGE_KEYWORDS.items():
            if other_stage != stage:
                assert keyword not in prompt

        assert self._RISK_KEYWORDS[risk] in prompt
        for other_risk, keyword in self._RISK_KEYWORDS.items():
            if other_risk != risk:
                assert keyword not in prompt


# ---------------------------------------------------------------------------
# Degraded Result Tests
# ---------------------------------------------------------------------------


class TestDegradedFeedbackResult:
    def test_degraded_result_valid(self):
        result = get_degraded_feedback_result()
        assert isinstance(result, WeeklyFeedbackResult)
        assert len(result.positive_changes) >= 1
        assert len(result.decision_options) == 3

    def test_degraded_result_boundary_clean(self):
        result = get_degraded_feedback_result()
        output = check_feedback_boundary(result)
        assert output.passed is True, f"降级结果不应触发边界检查：{output.flags}"

    def test_degraded_result_field_lengths(self):
        result = get_degraded_feedback_result()
        assert len(result.summary_text) <= 300
        assert len(result.conservative_path_note) <= 200
        for item in result.positive_changes:
            assert len(item.title) <= 25
            assert len(item.description) <= 200

    def test_degraded_decision_options_complete(self):
        result = get_degraded_feedback_result()
        values = {opt.value for opt in result.decision_options}
        assert values == {DecisionValue.CONTINUE, DecisionValue.LOWER_DIFFICULTY, DecisionValue.CHANGE_FOCUS}


# ---------------------------------------------------------------------------
# parse_weekly_feedback_result Tests
# ---------------------------------------------------------------------------


class TestParseWeeklyFeedbackResult:
    def test_valid_json(self):
        result = parse_weekly_feedback_result(_make_valid_feedback_json())
        assert len(result.positive_changes) == 1
        assert result.positive_changes[0].title == "洗澡转场更顺了"

    def test_invalid_json(self):
        with pytest.raises(Exception):
            parse_weekly_feedback_result("not json")

    def test_missing_positive_changes(self):
        data = json.loads(_make_valid_feedback_json())
        data["positive_changes"] = []
        with pytest.raises(ValidationError):
            parse_weekly_feedback_result(json.dumps(data))

    def test_decision_options_wrong_count(self):
        data = json.loads(_make_valid_feedback_json())
        data["decision_options"] = data["decision_options"][:2]
        with pytest.raises(ValidationError):
            parse_weekly_feedback_result(json.dumps(data))

    def test_positive_changes_missing_evidence(self):
        data = json.loads(_make_valid_feedback_json())
        data["positive_changes"][0]["supporting_evidence"] = None
        with pytest.raises(ValidationError):
            parse_weekly_feedback_result(json.dumps(data))


# ---------------------------------------------------------------------------
# Template Version Tests
# ---------------------------------------------------------------------------


class TestFeedbackTemplateVersion:
    def test_version_format(self):
        version = get_feedback_template_version()
        assert version == "tpl_weekly_feedback_v1/1.0.0"
        assert version == TEMPLATE_FULL_VERSION

    def test_version_contains_template_id(self):
        version = get_feedback_template_version()
        assert "tpl_weekly_feedback_v1" in version


# ---------------------------------------------------------------------------
# Boundary Check Tests for WeeklyFeedbackResult
# ---------------------------------------------------------------------------


class TestFeedbackBoundaryCheck:
    def test_clean_feedback_passes(self):
        result = parse_weekly_feedback_result(_make_valid_feedback_json())
        output = check_feedback_boundary(result)
        assert output.passed is True

    def test_diagnosis_label_in_feedback_detected(self):
        data = json.loads(_make_valid_feedback_json())
        data["positive_changes"][0]["description"] = "这不像是自闭的表现。"
        result = WeeklyFeedbackResult.model_validate(data)
        output = check_feedback_boundary(result)
        assert output.passed is False
        assert any(f.category == "diagnosis_label" for f in output.flags)

    def test_negate_child_in_opportunities(self):
        data = json.loads(_make_valid_feedback_json())
        data["opportunities"][0]["description"] = "孩子做不到这个能力。"
        result = WeeklyFeedbackResult.model_validate(data)
        output = check_feedback_boundary(result)
        assert output.passed is False
        assert any(f.category == "negate_child" for f in output.flags)
