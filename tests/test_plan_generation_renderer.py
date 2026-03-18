"""微计划生成渲染器集成测试。

覆盖：
- 完整渲染流程
- 9 种阶段 x 风险组合的输出验证
- 降级结果有效性
- parse_plan_generation_result 功能
- 模板版本一致性
- 边界检查（PlanGenerationResult）
"""

import json
from itertools import product

import pytest
from pydantic import ValidationError

from ai_parenting.models.enums import ChildStage, FocusTheme, RiskLevel
from ai_parenting.models.schemas import ContextSnapshot, PlanGenerationResult
from ai_parenting.renderer_plan_generation import (
    check_plan_boundary,
    get_degraded_plan_result,
    get_plan_template_version,
    parse_plan_generation_result,
    render_plan_generation_prompt,
)
from ai_parenting.templates.plan_generation import TEMPLATE_FULL_VERSION


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
        child_focus_themes=[FocusTheme.LANGUAGE],
        child_risk_level=risk,
        recent_record_keywords=["指向", "选择表达"],
    )


def _make_valid_plan_json() -> str:
    """构造一个合法的 PlanGenerationResult JSON 字符串。"""
    plan = {
        "title": "这周练习用动作和词语表达选择",
        "primary_goal": "在吃饭和选玩具的场景中练习表达",
        "focus_theme": "language",
        "priority_scenes": ["点心时间", "选玩具"],
        "day_tasks": [
            {
                "day_number": i,
                "main_exercise_title": f"Day {i} 主练习",
                "main_exercise_description": f"Day {i} 的主练习描述",
                "natural_embed_title": f"Day {i} 嵌入",
                "natural_embed_description": f"Day {i} 的嵌入描述",
                "demo_script": "你要苹果还是香蕉？",
                "observation_point": "观察孩子是否有回应。",
            }
            for i in range(1, 8)
        ],
        "observation_candidates": [
            {"id": f"oc_0{i}", "text": f"候选项{i}", "theme": "language", "default_selected": i <= 2}
            for i in range(1, 6)
        ],
        "weekend_review_prompt": "回想这周哪个场景最容易出现互动。",
        "conservative_note": "如果这周执行起来比较吃力，可以先只保留一个场景。",
    }
    return json.dumps(plan, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Basic Render Tests
# ---------------------------------------------------------------------------


class TestRenderPlanGenerationPrompt:
    def test_basic_render(self):
        ctx = _make_context()
        prompt = render_plan_generation_prompt(
            context=ctx,
            child_nickname="小明",
            recent_records_summary="最近记录：指向表达增多",
        )
        assert "7 天家庭微计划" in prompt
        assert "小明" in prompt
        assert "指向表达增多" in prompt

    def test_boundary_directives_injected(self):
        ctx = _make_context()
        prompt = render_plan_generation_prompt(context=ctx)
        assert "非诊断化边界" in prompt
        assert "绝对禁止使用的词汇" in prompt

    def test_output_format_present(self):
        ctx = _make_context()
        prompt = render_plan_generation_prompt(context=ctx)
        assert "day_tasks" in prompt
        assert "observation_candidates" in prompt
        assert "conservative_note" in prompt

    def test_weekly_rhythm_present(self):
        ctx = _make_context()
        prompt = render_plan_generation_prompt(context=ctx)
        assert "Day 1（建基线）" in prompt
        assert "Day 7（周总结）" in prompt

    def test_parent_language_style_present(self):
        ctx = _make_context()
        prompt = render_plan_generation_prompt(context=ctx)
        assert "家长语言风格指令" in prompt


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
        RiskLevel.NORMAL: "正常波动：计划语气",
        RiskLevel.ATTENTION: "重点关注：计划可以更明确",
        RiskLevel.CONSULT: "建议咨询——保守支持路径",
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
        prompt = render_plan_generation_prompt(
            context=ctx,
            child_nickname="宝宝",
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


class TestDegradedPlanResult:
    def test_degraded_result_valid(self):
        result = get_degraded_plan_result()
        assert isinstance(result, PlanGenerationResult)
        assert len(result.day_tasks) == 7
        assert len(result.observation_candidates) >= 5

    def test_degraded_result_boundary_clean(self):
        result = get_degraded_plan_result()
        output = check_plan_boundary(result)
        assert output.passed is True, f"降级结果不应触发边界检查：{output.flags}"

    def test_degraded_result_field_lengths(self):
        result = get_degraded_plan_result()
        assert len(result.title) <= 30
        assert len(result.primary_goal) <= 100
        assert len(result.weekend_review_prompt) <= 200
        assert len(result.conservative_note) <= 200
        for task in result.day_tasks:
            assert len(task.main_exercise_title) <= 25
            assert len(task.main_exercise_description) <= 300
            assert len(task.demo_script) <= 150


# ---------------------------------------------------------------------------
# parse_plan_generation_result Tests
# ---------------------------------------------------------------------------


class TestParsePlanGenerationResult:
    def test_valid_json(self):
        result = parse_plan_generation_result(_make_valid_plan_json())
        assert result.title == "这周练习用动作和词语表达选择"
        assert len(result.day_tasks) == 7

    def test_invalid_json(self):
        with pytest.raises(Exception):
            parse_plan_generation_result("not json")

    def test_missing_day_tasks(self):
        data = json.loads(_make_valid_plan_json())
        data["day_tasks"] = data["day_tasks"][:3]  # 只有 3 天
        with pytest.raises(ValidationError):
            parse_plan_generation_result(json.dumps(data))

    def test_observation_candidates_too_few(self):
        data = json.loads(_make_valid_plan_json())
        data["observation_candidates"] = data["observation_candidates"][:2]  # 只有 2 个
        with pytest.raises(ValidationError):
            parse_plan_generation_result(json.dumps(data))


# ---------------------------------------------------------------------------
# Template Version Tests
# ---------------------------------------------------------------------------


class TestPlanTemplateVersion:
    def test_version_format(self):
        version = get_plan_template_version()
        assert version == "tpl_plan_generation_v1/2.1.0"
        assert version == TEMPLATE_FULL_VERSION

    def test_version_contains_template_id(self):
        version = get_plan_template_version()
        assert "tpl_plan_generation_v1" in version


# ---------------------------------------------------------------------------
# Boundary Check Tests for PlanGenerationResult
# ---------------------------------------------------------------------------


class TestPlanBoundaryCheck:
    def test_clean_plan_passes(self):
        result = parse_plan_generation_result(_make_valid_plan_json())
        output = check_plan_boundary(result)
        assert output.passed is True

    def test_diagnosis_label_in_plan_detected(self):
        data = json.loads(_make_valid_plan_json())
        data["day_tasks"][0]["main_exercise_description"] = "这不像自闭的表现，多做练习。"
        result = PlanGenerationResult.model_validate(data)
        output = check_plan_boundary(result)
        assert output.passed is False
        assert any(f.category == "diagnosis_label" for f in output.flags)

    def test_treatment_promise_in_plan_detected(self):
        data = json.loads(_make_valid_plan_json())
        data["primary_goal"] = "通过训练好来解决问题"
        result = PlanGenerationResult.model_validate(data)
        output = check_plan_boundary(result)
        assert output.passed is False
        assert any(f.category == "treatment_promise" for f in output.flags)


# ---------------------------------------------------------------------------
# Feedback Context Injection Tests
# ---------------------------------------------------------------------------


class TestFeedbackContextInjection:
    """验证反馈回注上下文段正确注入 Prompt。"""

    def test_empty_feedback_context_no_placeholder(self):
        """空反馈上下文时，占位符应被清除。"""
        ctx = _make_context()
        prompt = render_plan_generation_prompt(
            context=ctx,
            feedback_context_text="",
        )
        assert "{{反馈回注上下文段}}" not in prompt

    def test_feedback_context_injected(self):
        """有反馈上下文时，文本应出现在 Prompt 中。"""
        ctx = _make_context()
        feedback_text = "【上周计划执行反馈——请据此调整本周计划】\n上周计划「选择表达周计划」完成率 71%。"
        prompt = render_plan_generation_prompt(
            context=ctx,
            feedback_context_text=feedback_text,
        )
        assert "上周计划执行反馈" in prompt
        assert "选择表达周计划" in prompt
        assert "71%" in prompt
        assert "{{反馈回注上下文段}}" not in prompt

    def test_feedback_context_position_between_risk_and_language(self):
        """反馈段应位于风险适配和家长语言风格之间。"""
        ctx = _make_context()
        feedback_text = "【上周计划执行反馈——MARKER——】"
        prompt = render_plan_generation_prompt(
            context=ctx,
            feedback_context_text=feedback_text,
        )
        risk_pos = prompt.find("正常波动：计划语气")
        feedback_pos = prompt.find("MARKER")
        language_pos = prompt.find("家长语言风格指令")
        assert risk_pos < feedback_pos < language_pos

    def test_feedback_context_does_not_break_boundary_directives(self):
        """反馈段注入不影响非诊断化边界指令。"""
        ctx = _make_context()
        feedback_text = "上周完成率 50%，家长选择降低难度。"
        prompt = render_plan_generation_prompt(
            context=ctx,
            feedback_context_text=feedback_text,
        )
        assert "非诊断化边界" in prompt
        assert "绝对禁止使用的词汇" in prompt

    def test_feedback_context_coexists_with_all_stages(self):
        """反馈段注入应与所有年龄阶段兼容。"""
        for stage, age in [
            (ChildStage.M18_24, 20),
            (ChildStage.M24_36, 30),
            (ChildStage.M36_48, 40),
        ]:
            ctx = _make_context(stage=stage, age=age)
            feedback_text = "上周完成率 80%。"
            prompt = render_plan_generation_prompt(
                context=ctx,
                feedback_context_text=feedback_text,
            )
            assert "上周完成率 80%" in prompt
