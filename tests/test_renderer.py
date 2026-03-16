"""渲染器集成测试。

覆盖：
- 完整渲染流程
- 9 种阶段 x 风险组合的输出验证
- 降级结果有效性
- parse_instant_help_result 功能
- 模板版本一致性
"""

import json
from itertools import product

import pytest
from pydantic import ValidationError

from ai_parenting.models.enums import ChildStage, FocusTheme, RiskLevel
from ai_parenting.models.schemas import ContextSnapshot, InstantHelpResult
from ai_parenting.renderer import (
    check_boundary,
    get_degraded_result,
    get_template_version,
    parse_instant_help_result,
    render_instant_help_prompt,
)
from ai_parenting.templates.instant_help import TEMPLATE_FULL_VERSION


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
        active_plan_id="plan-001",
        active_plan_day=3,
        recent_record_keywords=["指向", "选择表达"],
    )


# ---------------------------------------------------------------------------
# Basic Render Tests
# ---------------------------------------------------------------------------


class TestRenderInstantHelpPrompt:
    def test_basic_render(self):
        ctx = _make_context()
        prompt = render_instant_help_prompt(
            context=ctx,
            user_scenario="吃饭时不肯坐下",
            user_input_text="孩子一直站着吃",
            child_nickname="小明",
            active_plan_title="练习选择表达",
        )
        # 基本内容应存在
        assert "即时支持助手" in prompt
        assert "小明" in prompt
        assert "吃饭时不肯坐下" in prompt
        assert "孩子一直站着吃" in prompt

    def test_boundary_directives_injected(self):
        ctx = _make_context()
        prompt = render_instant_help_prompt(
            context=ctx,
            user_scenario="测试",
            user_input_text="测试",
        )
        assert "非诊断化边界" in prompt
        assert "绝对禁止使用的词汇" in prompt

    def test_output_format_present(self):
        ctx = _make_context()
        prompt = render_instant_help_prompt(
            context=ctx,
            user_scenario="测试",
            user_input_text="测试",
        )
        assert "step_one" in prompt
        assert "scenario_summary" in prompt
        assert "boundary_note" in prompt


# ---------------------------------------------------------------------------
# 9 Stage x Risk Combination Tests
# ---------------------------------------------------------------------------


class TestStageRiskCombinations:
    """验证全部 9 种 阶段 x 风险 组合的 Prompt 输出。"""

    _STAGE_KEYWORDS = {
        ChildStage.M18_24: "18-24 个月",
        ChildStage.M24_36: "24-36 个月",
        ChildStage.M36_48: "36-48 个月",
    }

    # 风险关键词使用更精确的匹配文本（完整的条件分支输出文本片段），
    # 避免与非诊断化指令块中的通用文本冲突
    _RISK_KEYWORDS = {
        RiskLevel.NORMAL: '当前风险层级为"正常波动"',
        RiskLevel.ATTENTION: '当前风险层级为"重点关注"',
        RiskLevel.CONSULT: '当前风险层级为"建议咨询"',
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
        prompt = render_instant_help_prompt(
            context=ctx,
            user_scenario="测试场景",
            user_input_text="测试描述",
            child_nickname="宝宝",
        )

        # 匹配的阶段关键词应出现
        assert self._STAGE_KEYWORDS[stage] in prompt
        # 不匹配的阶段关键词不应出现
        for other_stage, keyword in self._STAGE_KEYWORDS.items():
            if other_stage != stage:
                assert keyword not in prompt, (
                    f"阶段 {stage.value} 的 Prompt 中不应包含 {other_stage.value} 的关键词"
                )

        # 匹配的风险关键词应出现
        assert self._RISK_KEYWORDS[risk] in prompt
        # 不匹配的风险关键词不应出现
        for other_risk, keyword in self._RISK_KEYWORDS.items():
            if other_risk != risk:
                assert keyword not in prompt, (
                    f"风险 {risk.value} 的 Prompt 中不应包含 {other_risk.value} 的关键词"
                )


# ---------------------------------------------------------------------------
# Degraded Result Tests
# ---------------------------------------------------------------------------


class TestDegradedResult:
    def test_degraded_result_valid(self):
        result = get_degraded_result()
        assert isinstance(result, InstantHelpResult)
        assert result.step_one.title == "先稳住自己"
        assert result.step_two.title == "简短回应"
        assert result.step_three.title == "给双方空间"

    def test_degraded_result_boundary_clean(self):
        result = get_degraded_result()
        output = check_boundary(result)
        assert output.passed is True, f"降级结果不应触发边界检查：{output.flags}"

    def test_degraded_result_field_lengths(self):
        result = get_degraded_result()
        assert len(result.step_one.body) <= 200
        assert len(result.step_two.body) <= 300
        assert len(result.step_three.body) <= 300
        assert len(result.scenario_summary) <= 80
        assert len(result.boundary_note) <= 150


# ---------------------------------------------------------------------------
# parse_instant_help_result Tests
# ---------------------------------------------------------------------------


class TestParseInstantHelpResult:
    def test_valid_json(self):
        data = {
            "step_one": {"title": "标题", "body": "正文内容", "example_script": None},
            "step_two": {"title": "标题", "body": "正文内容", "example_script": None},
            "step_three": {"title": "标题", "body": "正文内容", "example_script": None},
            "scenario_summary": "场景摘要",
            "suggest_record": False,
            "suggest_add_focus": False,
            "suggest_consult_prep": False,
            "consult_prep_reason": None,
            "boundary_note": "边界说明",
        }
        result = parse_instant_help_result(json.dumps(data, ensure_ascii=False))
        assert result.step_one.title == "标题"

    def test_invalid_json(self):
        with pytest.raises(Exception):
            parse_instant_help_result("not json")

    def test_missing_required_field(self):
        data = {
            "step_one": {"title": "标题", "body": "正文"},
            # 缺少 step_two, step_three 等
        }
        with pytest.raises(ValidationError):
            parse_instant_help_result(json.dumps(data))


# ---------------------------------------------------------------------------
# Template Version Tests
# ---------------------------------------------------------------------------


class TestTemplateVersion:
    def test_version_format(self):
        version = get_template_version()
        assert version == "tpl_instant_help_v1/1.0.0"
        assert version == TEMPLATE_FULL_VERSION

    def test_version_contains_template_id(self):
        version = get_template_version()
        assert "tpl_instant_help_v1" in version
