"""微计划生成模板渲染器。

组装完整的 Prompt 渲染流程：
1. 加载模板常量（分段拼接）
2. 注入非诊断化指令块
3. 条件分支裁剪（根据 ContextSnapshot 中的 child_stage 和 child_risk_level）
4. 占位符替换（将 ContextSnapshot 字段注入模板）

公共接口：
- render_plan_generation_prompt(): 输入上下文，输出完整 Prompt 文本
- parse_plan_generation_result(): 解析模型返回的 JSON 为 PlanGenerationResult
- check_plan_boundary(): 对 PlanGenerationResult 执行边界检查
- get_degraded_plan_result(): 获取降级版结果
- get_plan_template_version(): 获取模板版本号
"""

from __future__ import annotations

from ai_parenting.engine.boundary_checker import BoundaryChecker, BoundaryCheckOutput
from ai_parenting.engine.template_engine import render
from ai_parenting.models.schemas import ContextSnapshot, PlanGenerationResult
from ai_parenting.templates.boundary_directives import BOUNDARY_DIRECTIVES_BLOCK
from ai_parenting.templates.degraded import DEGRADED_PLAN_GENERATION_RESULT
from ai_parenting.templates.plan_generation import (
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


def render_plan_generation_prompt(
    context: ContextSnapshot,
    child_nickname: str = "",
    recent_records_summary: str = "",
) -> str:
    """渲染微计划生成 Prompt。

    完成模板加载 → 指令块注入 → 条件裁剪 → 占位符替换的完整流程。

    Args:
        context: 儿童上下文快照。
        child_nickname: 儿童昵称。
        recent_records_summary: 最近记录摘要文本。

    Returns:
        完整的、可直接发送给模型的 Prompt 文本。
    """
    # Step 1: 注入非诊断化指令块
    template_with_directives = FULL_TEMPLATE.replace(
        BOUNDARY_PLACEHOLDER, BOUNDARY_DIRECTIVES_BLOCK
    )

    # Step 2 & 3: 条件裁剪 + 占位符替换
    condition_context: dict[str, str] = {
        "child_stage": context.child_stage.value,
        "child_risk_level": context.child_risk_level.value,
    }

    placeholder_variables: dict[str, str] = {
        "child_nickname": child_nickname,
        "child_age_months": str(context.child_age_months),
        "child_stage": context.child_stage.value,
        "child_focus_themes": ", ".join(
            t.value for t in context.child_focus_themes
        ) if context.child_focus_themes else "暂无",
        "child_risk_level": context.child_risk_level.value,
        "recent_record_keywords": ", ".join(context.recent_record_keywords) if context.recent_record_keywords else "暂无",
        "recent_records_summary": recent_records_summary or "暂无最近记录摘要",
        "prompt_template_version": TEMPLATE_FULL_VERSION,
    }

    return render(template_with_directives, condition_context, placeholder_variables)


def parse_plan_generation_result(raw_json: str) -> PlanGenerationResult:
    """解析模型返回的 JSON 为 PlanGenerationResult。

    Args:
        raw_json: 模型返回的 JSON 字符串。

    Returns:
        校验通过的 PlanGenerationResult 实例。

    Raises:
        pydantic.ValidationError: 结构不合格或约束不满足。
        json.JSONDecodeError: JSON 解析失败。
    """
    return PlanGenerationResult.model_validate_json(raw_json)


def check_plan_boundary(result: PlanGenerationResult) -> BoundaryCheckOutput:
    """对 PlanGenerationResult 执行非诊断化边界检查。

    Args:
        result: 待检查的微计划生成结果。

    Returns:
        BoundaryCheckOutput，包含通过状态、标记列表和清洁结果。
    """
    return _boundary_checker.check(result)


def get_degraded_plan_result() -> PlanGenerationResult:
    """获取降级版微计划生成结果。

    当模型超时、结构不合格或边界检查多次不通过时使用。

    Returns:
        预构建的降级 PlanGenerationResult 实例。
    """
    return DEGRADED_PLAN_GENERATION_RESULT


def get_plan_template_version() -> str:
    """获取当前模板版本号。

    Returns:
        模板完整版本字符串（如 "tpl_plan_generation_v1/1.0.0"）。
    """
    return TEMPLATE_FULL_VERSION
