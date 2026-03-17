"""即时求助 SkillAdapter。

将现有 renderer.py（即时求助渲染器）包装为 Skill 接口。
Phase 3 升级：supports_orchestrate=True，Orchestrator 通过统一接口调用。
"""

from __future__ import annotations

import logging
from typing import Any

from pydantic import BaseModel

from ai_parenting.skills.base import BoundaryRule, Skill, SkillMetadata, SkillResult

logger = logging.getLogger(__name__)


class InstantHelpAdapter(Skill):
    """即时求助技能适配器。

    包装 renderer.py 的函数为统一的 Skill 接口，
    同时支持 Orchestrator 模式（render → call → parse → check）
    和简单模式（直接 execute）。
    """

    @property
    def metadata(self) -> SkillMetadata:
        return SkillMetadata(
            name="instant_help",
            display_name="即时求助",
            description="带娃遇到问题，随时问 AI 获取育儿指导",
            version="1.0.0",
            icon="💬",
            tags=["help", "ask", "question", "求助", "怎么办"],
            session_type="instant_help",
        )

    @property
    def supports_orchestrate(self) -> bool:
        return True

    def get_timeout_config(self) -> tuple[float, float]:
        return (8.0, 12.0)

    # ------------------------------------------------------------------
    # Orchestrator 模式方法
    # ------------------------------------------------------------------

    def render_prompt(self, context: Any, **kwargs: Any) -> str:
        from ai_parenting.renderer import render_instant_help_prompt

        return render_instant_help_prompt(
            context=context,
            user_scenario=kwargs.get("user_scenario", ""),
            user_input_text=kwargs.get("user_input_text", ""),
            child_nickname=kwargs.get("child_nickname", ""),
            active_plan_title=kwargs.get("active_plan_title", ""),
            recent_records_summary=kwargs.get("recent_records_summary", ""),
        )

    def parse_result(self, raw_json: str) -> BaseModel:
        from ai_parenting.renderer import parse_instant_help_result

        return parse_instant_help_result(raw_json)

    def check_boundary(self, result: BaseModel) -> Any:
        from ai_parenting.renderer import check_boundary

        return check_boundary(result)  # type: ignore[arg-type]

    def get_degraded_result(self) -> BaseModel:
        from ai_parenting.renderer import get_degraded_result

        return get_degraded_result()

    def get_template_version(self) -> str:
        from ai_parenting.renderer import get_template_version

        return get_template_version()

    # ------------------------------------------------------------------
    # 简单模式（VoicePipeline 等直接调用）
    # ------------------------------------------------------------------

    async def execute(self, params: dict[str, Any], context: Any) -> SkillResult:
        """执行即时求助。

        params 中期望的字段：
        - user_scenario: str — 用户描述的场景
        - user_input_text: str — 用户输入的问题文本
        - child_nickname: str — 孩子昵称（可选）
        - active_plan_title: str — 当前计划标题（可选）
        - recent_records_summary: str — 最近记录摘要（可选）

        context: ContextSnapshot 实例
        """
        try:
            from ai_parenting.renderer import (
                check_boundary,
                get_degraded_result,
                parse_instant_help_result,
                render_instant_help_prompt,
            )
            from ai_parenting.providers.base import ModelProvider

            # 1. 渲染 prompt
            prompt = render_instant_help_prompt(
                context=context,
                user_scenario=params.get("user_scenario", ""),
                user_input_text=params.get("user_input_text", ""),
                child_nickname=params.get("child_nickname", ""),
                active_plan_title=params.get("active_plan_title", ""),
                recent_records_summary=params.get("recent_records_summary", ""),
            )

            # 2. 如果提供了 provider，调用 AI 生成
            provider: ModelProvider | None = params.get("_provider")
            if provider is None:
                # 没有 provider 时返回降级结果
                degraded = get_degraded_result()
                return SkillResult(
                    response_text=degraded.answer if hasattr(degraded, "answer") else str(degraded),
                    structured_data=degraded,
                    boundary_passed=True,
                    is_degraded=True,
                )

            raw_json = await provider.generate(prompt)

            # 3. 解析结果
            result = parse_instant_help_result(raw_json)

            # 4. 安全边界检查
            boundary_output = check_boundary(result)
            if boundary_output.cleaned_result:
                result = boundary_output.cleaned_result

            response_text = result.answer if hasattr(result, "answer") else str(result)

            return SkillResult(
                response_text=response_text,
                structured_data=result,
                boundary_passed=boundary_output.passed,
                metadata={"flags_count": len(boundary_output.flags)},
            )

        except Exception as exc:
            logger.error("InstantHelpAdapter execute failed: %s", exc)
            # 降级处理
            try:
                from ai_parenting.renderer import get_degraded_result
                degraded = get_degraded_result()
                return SkillResult(
                    response_text=str(degraded),
                    structured_data=degraded,
                    boundary_passed=True,
                    is_degraded=True,
                    metadata={"error": str(exc)},
                )
            except Exception:
                return SkillResult(
                    response_text="抱歉，暂时无法回答您的问题，请稍后再试。",
                    boundary_passed=True,
                    is_degraded=True,
                    metadata={"error": str(exc)},
                )

    def get_boundary_rules(self) -> list[BoundaryRule]:
        return [
            BoundaryRule(
                category="diagnosis_label",
                description="禁止在即时求助回复中出现医学诊断标签",
            ),
            BoundaryRule(
                category="treatment_promise",
                description="禁止承诺治疗效果或使用绝对性治疗表述",
            ),
            BoundaryRule(
                category="blame_parent",
                description="禁止责备家长的表述",
            ),
            BoundaryRule(
                category="negate_child",
                description="禁止否定儿童的表述",
            ),
        ]
