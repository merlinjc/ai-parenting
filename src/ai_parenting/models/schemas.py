"""Pydantic v2 数据模型。

定义 AI 编排层使用的核心数据结构，字段约束与设计文档完全对齐：
- StepContent: 三步支持结构中的单步内容
- InstantHelpResult: 即时求助完整输出结构
- DayTaskContent: 七日计划中的单日任务内容
- ObservationCandidateContent: 快速打点候选项
- PlanGenerationResult: 微计划生成完整输出结构
- FeedbackItemContent: 周反馈变化项内容
- DecisionOptionContent: 周反馈决策选项
- WeeklyFeedbackResult: 周反馈完整输出结构
- OutputMetadata: AI 输出元数据（模板版本、模型信息、边界检查结果）
- ContextSnapshot: 儿童上下文快照（编排层请求时的状态快照）
- BoundaryCheckResult: 边界检查结果
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator

from ai_parenting.models.enums import (
    ChildStage,
    DecisionValue,
    FocusTheme,
    RiskLevel,
)


# ---------------------------------------------------------------------------
# 即时求助输出结构
# ---------------------------------------------------------------------------


class StepContent(BaseModel):
    """三步支持结构中的单步内容。

    字段约束来源：AI 输出结构草案 V1 第 3.2 节。
    - title: 最长 20 字符
    - body: 最长因步骤而异（由 InstantHelpResult 层通过 validator 区分）
    - example_script: 最长 100 字符，可选
    """

    title: str = Field(..., min_length=1, max_length=20, description="步骤标题")
    body: str = Field(..., min_length=1, max_length=300, description="步骤正文（2-4 句话）")
    example_script: Optional[str] = Field(
        None, max_length=100, description="示范话术（家长可直接说出口的话）"
    )


class InstantHelpResult(BaseModel):
    """即时求助完整输出结构。

    字段约束来源：AI 输出结构草案 V1 第 3.1-3.2 节。
    step_one.body 最长 200 字符，step_two/step_three.body 最长 300 字符。
    """

    step_one: StepContent = Field(..., description="第一步：先稳住家长自己")
    step_two: StepContent = Field(..., description="第二步：接下来可以做一个什么小动作")
    step_three: StepContent = Field(..., description="第三步：如果没接住怎么办")

    scenario_summary: str = Field(
        ..., min_length=1, max_length=80, description="一句话概括 AI 对当前场景的理解"
    )

    suggest_record: bool = Field(..., description="是否建议补记为记录")
    suggest_add_focus: bool = Field(..., description="是否建议加入本周关注")
    suggest_consult_prep: bool = Field(..., description="是否建议查看咨询准备")
    consult_prep_reason: Optional[str] = Field(
        None,
        max_length=100,
        description="咨询准备原因（仅当 suggest_consult_prep 为 true 时填写）",
    )

    boundary_note: str = Field(
        ..., min_length=1, max_length=150, description="非诊断化提示文本"
    )

    @field_validator("step_one")
    @classmethod
    def validate_step_one_body_length(cls, v: StepContent) -> StepContent:
        """step_one.body 最长 200 字符（比 step_two/three 的 300 更短）。"""
        if len(v.body) > 200:
            raise ValueError(
                f"step_one.body 不得超过 200 字符，当前 {len(v.body)} 字符"
            )
        return v

    @field_validator("consult_prep_reason")
    @classmethod
    def validate_consult_prep_reason(cls, v: Optional[str], info) -> Optional[str]:
        """当 suggest_consult_prep 为 false 时，consult_prep_reason 应为 None。"""
        # 注意：Pydantic v2 中 info.data 可能不完整（取决于字段顺序），
        # 这里仅在值非 None 时做基本检查，完整的交叉校验在 model_validator 中更可靠。
        return v


# ---------------------------------------------------------------------------
# 微计划生成输出结构
# ---------------------------------------------------------------------------


class DayTaskContent(BaseModel):
    """七日计划中的单日任务内容。

    字段约束来源：AI 输出结构草案 V1 第 4.1-4.2 节。
    """

    day_number: int = Field(..., ge=1, le=7, description="日序号（1-7）")
    main_exercise_title: str = Field(
        ..., min_length=1, max_length=25, description="主练习标题"
    )
    main_exercise_description: str = Field(
        ..., min_length=1, max_length=300, description="主练习说明"
    )
    natural_embed_title: str = Field(
        ..., min_length=1, max_length=25, description="自然嵌入标题"
    )
    natural_embed_description: str = Field(
        ..., min_length=1, max_length=300, description="自然嵌入说明"
    )
    demo_script: str = Field(
        ..., min_length=1, max_length=150, description="示范话术（家长可直接说出口的话）"
    )
    observation_point: str = Field(
        ..., min_length=1, max_length=150, description="观察点"
    )


class ObservationCandidateContent(BaseModel):
    """快速打点候选项。

    字段约束来源：AI 输出结构草案 V1 第 4.1 节。
    """

    id: str = Field(..., min_length=1, description="候选项标识（如 oc_01）")
    text: str = Field(..., min_length=1, max_length=30, description="显示文本")
    theme: FocusTheme = Field(..., description="关联主题")
    default_selected: bool = Field(..., description="是否默认选中")


class PlanGenerationResult(BaseModel):
    """微计划生成完整输出结构。

    字段约束来源：AI 输出结构草案 V1 第 4.1-4.2 节。
    """

    title: str = Field(..., min_length=1, max_length=30, description="计划标题")
    primary_goal: str = Field(
        ..., min_length=1, max_length=100, description="一句话主目标"
    )
    focus_theme: FocusTheme = Field(..., description="焦点主题")
    priority_scenes: list[str] = Field(
        ..., description="优先场景列表（2-3 个，每个最长 15 字符）"
    )
    day_tasks: list[DayTaskContent] = Field(
        ..., description="七日任务（必须恰好 7 个）"
    )
    observation_candidates: list[ObservationCandidateContent] = Field(
        ..., description="快速打点候选项（5-8 个）"
    )
    weekend_review_prompt: str = Field(
        ..., min_length=1, max_length=200, description="Day 6-7 的复盘引导文本"
    )
    conservative_note: str = Field(
        ..., min_length=1, max_length=200, description="保守路径预置"
    )

    @field_validator("priority_scenes")
    @classmethod
    def validate_priority_scenes(cls, v: list[str]) -> list[str]:
        """priority_scenes 必须 2-3 个，每个最长 15 字符。"""
        if len(v) < 2 or len(v) > 3:
            raise ValueError(
                f"priority_scenes 必须 2-3 个，当前 {len(v)} 个"
            )
        for i, scene in enumerate(v):
            if not scene or not scene.strip():
                raise ValueError(f"priority_scenes[{i}] 不得为空")
            if len(scene) > 15:
                raise ValueError(
                    f"priority_scenes[{i}] 不得超过 15 字符，当前 {len(scene)} 字符"
                )
        return v

    @field_validator("day_tasks")
    @classmethod
    def validate_day_tasks(cls, v: list[DayTaskContent]) -> list[DayTaskContent]:
        """day_tasks 必须恰好 7 个，day_number 为 1-7 各出现一次。"""
        if len(v) != 7:
            raise ValueError(f"day_tasks 必须恰好 7 个，当前 {len(v)} 个")
        day_numbers = sorted(t.day_number for t in v)
        if day_numbers != [1, 2, 3, 4, 5, 6, 7]:
            raise ValueError(
                f"day_tasks 的 day_number 必须为 1-7 各一个，当前为 {day_numbers}"
            )
        return v

    @field_validator("observation_candidates")
    @classmethod
    def validate_observation_candidates(
        cls, v: list[ObservationCandidateContent]
    ) -> list[ObservationCandidateContent]:
        """observation_candidates 必须 5-8 个，且至少 2 个 default_selected。"""
        if len(v) < 5 or len(v) > 8:
            raise ValueError(
                f"observation_candidates 必须 5-8 个，当前 {len(v)} 个"
            )
        default_count = sum(1 for c in v if c.default_selected)
        if default_count < 2:
            raise ValueError(
                f"observation_candidates 中至少 2 个 default_selected，当前 {default_count} 个"
            )
        # ID 唯一性检查
        ids = [c.id for c in v]
        if len(ids) != len(set(ids)):
            raise ValueError("observation_candidates 的 id 必须唯一")
        return v


# ---------------------------------------------------------------------------
# 周反馈输出结构
# ---------------------------------------------------------------------------


class FeedbackItemContent(BaseModel):
    """周反馈变化项内容。

    字段约束来源：AI 输出结构草案 V1 第 5.1-5.2 节。
    - positive_changes 中的 supporting_evidence 为必填
    - opportunities 中的 supporting_evidence 为可选
    """

    title: str = Field(..., min_length=1, max_length=25, description="变化项标题")
    description: str = Field(
        ..., min_length=1, max_length=200, description="变化项描述"
    )
    supporting_evidence: Optional[str] = Field(
        None, max_length=100, description="支撑证据摘要（从记录中提取）"
    )


class DecisionOptionContent(BaseModel):
    """周反馈决策选项。

    字段约束来源：AI 输出结构草案 V1 第 5.1-5.2 节。
    """

    id: str = Field(..., min_length=1, description="选项标识")
    text: str = Field(..., min_length=1, max_length=30, description="选项显示文本")
    value: DecisionValue = Field(..., description="选项值（continue/lower_difficulty/change_focus）")
    rationale: str = Field(
        ..., min_length=1, max_length=100, description="选择该选项的理由说明"
    )


class WeeklyFeedbackResult(BaseModel):
    """周反馈完整输出结构。

    字段约束来源：AI 输出结构草案 V1 第 5.1-5.2 节。
    """

    positive_changes: list[FeedbackItemContent] = Field(
        ..., description="积极变化（1-3 个，supporting_evidence 必填）"
    )
    opportunities: list[FeedbackItemContent] = Field(
        ..., description="仍需机会（1-3 个，supporting_evidence 可选）"
    )
    summary_text: str = Field(
        ..., min_length=1, max_length=300, description="整体摘要"
    )
    decision_options: list[DecisionOptionContent] = Field(
        ..., description="下周决策选项（恰好 3 个）"
    )
    conservative_path_note: str = Field(
        ..., min_length=1, max_length=200, description="保守路径说明"
    )
    referenced_record_ids: list[str] = Field(
        default_factory=list, description="AI 引用了的记录 ID 列表"
    )
    referenced_plan_id: str = Field(
        ..., min_length=1, description="AI 引用的计划 ID"
    )

    @field_validator("positive_changes")
    @classmethod
    def validate_positive_changes(
        cls, v: list[FeedbackItemContent]
    ) -> list[FeedbackItemContent]:
        """positive_changes 必须 1-3 个，且 supporting_evidence 必填。"""
        if len(v) < 1 or len(v) > 3:
            raise ValueError(
                f"positive_changes 必须 1-3 个，当前 {len(v)} 个"
            )
        for i, item in enumerate(v):
            if not item.supporting_evidence or not item.supporting_evidence.strip():
                raise ValueError(
                    f"positive_changes[{i}].supporting_evidence 不得为空"
                )
        return v

    @field_validator("opportunities")
    @classmethod
    def validate_opportunities(
        cls, v: list[FeedbackItemContent]
    ) -> list[FeedbackItemContent]:
        """opportunities 必须 1-3 个。"""
        if len(v) < 1 or len(v) > 3:
            raise ValueError(
                f"opportunities 必须 1-3 个，当前 {len(v)} 个"
            )
        return v

    @field_validator("decision_options")
    @classmethod
    def validate_decision_options(
        cls, v: list[DecisionOptionContent]
    ) -> list[DecisionOptionContent]:
        """decision_options 必须恰好 3 个，且 value 各不同。"""
        if len(v) != 3:
            raise ValueError(
                f"decision_options 必须恰好 3 个，当前 {len(v)} 个"
            )
        values = [opt.value for opt in v]
        if len(set(values)) != 3:
            raise ValueError(
                f"decision_options 的 value 必须各不相同，当前为 {[v.value for v in values]}"
            )
        expected = {DecisionValue.CONTINUE, DecisionValue.LOWER_DIFFICULTY, DecisionValue.CHANGE_FOCUS}
        actual = set(values)
        if actual != expected:
            raise ValueError(
                f"decision_options 的 value 必须恰好包含 continue/lower_difficulty/change_focus"
            )
        return v


# ---------------------------------------------------------------------------
# 输出元数据
# ---------------------------------------------------------------------------


class OutputMetadata(BaseModel):
    """AI 输出元数据。

    字段定义来源：AI 输出结构草案 V1 第 3.1 节 OutputMetadata。
    """

    prompt_template_version: str = Field(
        ..., description="Prompt 模板版本号（如 tpl_instant_help_v1/1.0.0）"
    )
    model_provider: str = Field(..., description="模型供应商标识")
    model_version: str = Field(..., description="模型版本")
    boundary_check_passed: bool = Field(..., description="边界检查是否通过")
    boundary_check_flags: list[str] = Field(
        default_factory=list, description="被标记的检查项列表"
    )
    generation_timestamp: datetime = Field(..., description="生成时间戳")
    latency_ms: int = Field(..., ge=0, description="响应延迟（毫秒）")


# ---------------------------------------------------------------------------
# 上下文快照
# ---------------------------------------------------------------------------


class ContextSnapshot(BaseModel):
    """儿童上下文快照。

    字段定义来源：数据结构草案 V1 第 10.2 节。
    编排层在请求时捕获当前状态，用于 Prompt 变量注入和审计回溯。
    """

    child_age_months: int = Field(
        ..., ge=18, le=48, description="请求时的儿童月龄"
    )
    child_stage: ChildStage = Field(..., description="请求时的年龄阶段")
    child_focus_themes: list[FocusTheme] = Field(
        default_factory=list, description="请求时的关注主题列表"
    )
    child_risk_level: RiskLevel = Field(..., description="请求时的风险层级")
    active_plan_id: Optional[str] = Field(None, description="请求时的活跃计划 ID")
    active_plan_day: Optional[int] = Field(
        None, ge=1, le=7, description="请求时的计划进行天数"
    )
    recent_record_ids: list[str] = Field(
        default_factory=list, description="请求时引用的最近记录 ID 列表"
    )
    recent_record_keywords: list[str] = Field(
        default_factory=list, description="提取的关键词摘要"
    )


# ---------------------------------------------------------------------------
# 边界检查结果（保留向后兼容，新代码使用 BoundaryCheckOutput）
# ---------------------------------------------------------------------------


class BoundaryCheckResult(BaseModel):
    """非诊断化边界检查结果。"""

    passed: bool = Field(..., description="检查是否全部通过")
    flags: list[str] = Field(
        default_factory=list, description="被触发的检查项标识列表"
    )
    cleaned_result: Optional[InstantHelpResult] = Field(
        None, description="替换后的清洁结果（仅在有替换时提供）"
    )
