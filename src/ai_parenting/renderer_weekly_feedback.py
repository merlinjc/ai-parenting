"""周反馈模板渲染器。

组装完整的 Prompt 渲染流程：
1. 加载模板常量（分段拼接）
2. 注入非诊断化指令块
3. 预处理特殊条件（record_count_this_week < 2 → record_insufficient）
4. 条件分支裁剪
5. 占位符替换

特殊处理：
原设计文档中 {{#if record_count_this_week < 2}} 使用了 < 运算符，
但引擎仅支持 ==。渲染器层负责预计算 record_insufficient 布尔值，
在条件上下文中传入 "true" 或 "false"。

公共接口：
- render_weekly_feedback_prompt(): 输入上下文和周反馈专属参数，输出完整 Prompt 文本
- parse_weekly_feedback_result(): 解析模型返回的 JSON 为 WeeklyFeedbackResult
- check_feedback_boundary(): 对 WeeklyFeedbackResult 执行边界检查
- get_degraded_feedback_result(): 获取降级版结果
- get_feedback_template_version(): 获取模板版本号
"""

from __future__ import annotations

from ai_parenting.engine.boundary_checker import BoundaryChecker, BoundaryCheckOutput
from ai_parenting.engine.template_engine import render
from ai_parenting.models.schemas import ContextSnapshot, WeeklyFeedbackResult
from ai_parenting.templates.boundary_directives import BOUNDARY_DIRECTIVES_BLOCK
from ai_parenting.templates.degraded import DEGRADED_WEEKLY_FEEDBACK_RESULT
from ai_parenting.templates.weekly_feedback import (
    BOUNDARY_PLACEHOLDER,
    FULL_TEMPLATE,
    TEMPLATE_FULL_VERSION,
)


# ---------------------------------------------------------------------------
# 模块级单例
# ---------------------------------------------------------------------------

_boundary_checker = BoundaryChecker()


# ---------------------------------------------------------------------------
# 公共接口
# ---------------------------------------------------------------------------


def render_weekly_feedback_prompt(
    context: ContextSnapshot,
    child_nickname: str = "",
    active_plan_title: str = "",
    active_plan_focus_theme: str = "",
    plan_completion_rate: str = "",
    record_count_this_week: int = 0,
    day_tasks_summary: str = "",
    weekly_records_detail: str = "",
    active_plan_id: str = "",
) -> str:
    """渲染周反馈 Prompt。

    完成模板加载 → 指令块注入 → 特殊条件预处理 → 条件裁剪 → 占位符替换。

    Args:
        context: 儿童上下文快照。
        child_nickname: 儿童昵称。
        active_plan_title: 当前活跃计划标题。
        active_plan_focus_theme: 当前计划焦点主题。
        plan_completion_rate: 本周计划完成率。
        record_count_this_week: 本周记录条数。
        day_tasks_summary: 7 天任务完成情况摘要。
        weekly_records_detail: 本周所有记录的结构化摘要。
        active_plan_id: 当前活跃计划 ID。

    Returns:
        完整的、可直接发送给模型的 Prompt 文本。
    """
    # Step 1: 注入非诊断化指令块
    template_with_directives = FULL_TEMPLATE.replace(
        BOUNDARY_PLACEHOLDER, BOUNDARY_DIRECTIVES_BLOCK
    )

    # Step 2: 预处理特殊条件 record_count_this_week < 2
    record_insufficient = "true" if record_count_this_week < 2 else "false"

    # Step 3 & 4: 条件裁剪 + 占位符替换
    condition_context: dict[str, str] = {
        "child_stage": context.child_stage.value,
        "child_risk_level": context.child_risk_level.value,
        "record_insufficient": record_insufficient,
    }

    placeholder_variables: dict[str, str] = {
        "child_nickname": child_nickname,
        "child_age_months": str(context.child_age_months),
        "child_stage": context.child_stage.value,
        "child_focus_themes": ", ".join(
            t.value for t in context.child_focus_themes
        ) if context.child_focus_themes else "暂无",
        "child_risk_level": context.child_risk_level.value,
        "active_plan_title": active_plan_title or "暂无活跃计划",
        "active_plan_focus_theme": active_plan_focus_theme or "暂无",
        "plan_completion_rate": plan_completion_rate or "0%",
        "record_count_this_week": str(record_count_this_week),
        "day_tasks_summary": day_tasks_summary or "暂无任务完成情况摘要",
        "weekly_records_detail": weekly_records_detail or "暂无本周观察记录",
        "active_plan_id": active_plan_id or "N/A",
        "prompt_template_version": TEMPLATE_FULL_VERSION,
    }

    return render(template_with_directives, condition_context, placeholder_variables)


def parse_weekly_feedback_result(raw_json: str) -> WeeklyFeedbackResult:
    """解析模型返回的 JSON 为 WeeklyFeedbackResult。

    Args:
        raw_json: 模型返回的 JSON 字符串。

    Returns:
        校验通过的 WeeklyFeedbackResult 实例。

    Raises:
        pydantic.ValidationError: 结构不合格或约束不满足。
        json.JSONDecodeError: JSON 解析失败。
    """
    return WeeklyFeedbackResult.model_validate_json(raw_json)


def check_feedback_boundary(result: WeeklyFeedbackResult) -> BoundaryCheckOutput:
    """对 WeeklyFeedbackResult 执行非诊断化边界检查。

    Args:
        result: 待检查的周反馈结果。

    Returns:
        BoundaryCheckOutput，包含通过状态、标记列表和清洁结果。
    """
    return _boundary_checker.check(result)


def get_degraded_feedback_result() -> WeeklyFeedbackResult:
    """获取降级版周反馈结果。

    当模型超时、结构不合格或边界检查多次不通过时使用。

    Returns:
        预构建的降级 WeeklyFeedbackResult 实例。
    """
    return DEGRADED_WEEKLY_FEEDBACK_RESULT


def get_feedback_template_version() -> str:
    """获取当前模板版本号。

    Returns:
        模板完整版本字符串（如 "tpl_weekly_feedback_v1/1.0.0"）。
    """
    return TEMPLATE_FULL_VERSION
