"""即时求助模板渲染器。

组装完整的 Prompt 渲染流程：
1. 加载模板常量（分段拼接）
2. 注入非诊断化指令块
3. 条件分支裁剪（根据 ContextSnapshot 中的 child_stage 和 child_risk_level）
4. 占位符替换（将 ContextSnapshot 字段和即时求助专属字段注入模板）

公共接口：
- render_instant_help_prompt(): 输入上下文和用户输入，输出完整 Prompt 文本
- parse_instant_help_result(): 解析模型返回的 JSON 为 InstantHelpResult
"""

from __future__ import annotations

import json
from typing import Optional

from ai_parenting.engine.boundary_checker import BoundaryChecker, BoundaryCheckOutput
from ai_parenting.engine.template_engine import render
from ai_parenting.models.schemas import ContextSnapshot, InstantHelpResult
from ai_parenting.templates.boundary_directives import BOUNDARY_DIRECTIVES_BLOCK
from ai_parenting.templates.degraded import DEGRADED_INSTANT_HELP_RESULT
from ai_parenting.templates.instant_help import (
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


def render_instant_help_prompt(
    context: ContextSnapshot,
    user_scenario: str,
    user_input_text: str,
    child_nickname: str = "",
    active_plan_title: str = "",
    recent_records_summary: str = "",
) -> str:
    """渲染即时求助 Prompt。

    完成模板加载 → 指令块注入 → 条件裁剪 → 占位符替换的完整流程。

    Args:
        context: 儿童上下文快照。
        user_scenario: 用户选择的问题场景。
        user_input_text: 用户自由输入文本。
        child_nickname: 儿童昵称（用于模板中 {{child_nickname}} 替换）。
        active_plan_title: 当前活跃计划标题（用于模板中 {{active_plan_title}} 替换）。
        recent_records_summary: 最近记录摘要文本（用于模板中 {{recent_records_summary}} 替换）。

    Returns:
        完整的、可直接发送给模型的 Prompt 文本。
    """
    # Step 1: 注入非诊断化指令块
    template_with_directives = FULL_TEMPLATE.replace(
        BOUNDARY_PLACEHOLDER, BOUNDARY_DIRECTIVES_BLOCK
    )

    # Step 2 & 3: 条件裁剪 + 占位符替换
    # 条件分支使用的上下文变量
    condition_context: dict[str, str] = {
        "child_stage": context.child_stage.value,
        "child_risk_level": context.child_risk_level.value,
    }

    # 占位符替换变量
    placeholder_variables: dict[str, str] = {
        "child_nickname": child_nickname,
        "child_age_months": str(context.child_age_months),
        "child_stage": context.child_stage.value,
        "child_focus_themes": ", ".join(
            t.value for t in context.child_focus_themes
        ) if context.child_focus_themes else "暂无",
        "child_risk_level": context.child_risk_level.value,
        "active_plan_title": active_plan_title or "暂无活跃计划",
        "active_plan_day": str(context.active_plan_day) if context.active_plan_day else "N/A",
        "recent_record_keywords": ", ".join(context.recent_record_keywords) if context.recent_record_keywords else "暂无",
        "recent_records_summary": recent_records_summary or "暂无最近记录摘要",
        "user_scenario": user_scenario,
        "user_input_text": user_input_text,
        "prompt_template_version": TEMPLATE_FULL_VERSION,
    }

    return render(template_with_directives, condition_context, placeholder_variables)


def parse_instant_help_result(raw_json: str) -> InstantHelpResult:
    """解析模型返回的 JSON 为 InstantHelpResult。

    使用 Pydantic v2 的 model_validate_json 完成结构 + 约束一次性校验。

    Args:
        raw_json: 模型返回的 JSON 字符串。

    Returns:
        校验通过的 InstantHelpResult 实例。

    Raises:
        pydantic.ValidationError: 结构不合格或约束不满足。
        json.JSONDecodeError: JSON 解析失败。
    """
    return InstantHelpResult.model_validate_json(raw_json)


def check_boundary(result: InstantHelpResult) -> BoundaryCheckOutput:
    """对 InstantHelpResult 执行非诊断化边界检查。

    Args:
        result: 待检查的即时求助结果。

    Returns:
        BoundaryCheckOutput，包含通过状态、标记列表和清洁结果。
    """
    return _boundary_checker.check(result)


def get_degraded_result() -> InstantHelpResult:
    """获取降级版即时求助结果。

    当模型超时、结构不合格或边界检查多次不通过时使用。

    Returns:
        预构建的降级 InstantHelpResult 实例。
    """
    return DEGRADED_INSTANT_HELP_RESULT


def get_template_version() -> str:
    """获取当前模板版本号。

    Returns:
        模板完整版本字符串（如 "tpl_instant_help_v1/1.0.0"）。
    """
    return TEMPLATE_FULL_VERSION
