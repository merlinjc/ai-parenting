"""周反馈 SkillAdapter。

将现有 renderer_weekly_feedback.py 包装为 Skill 接口。
Phase 3 升级：supports_orchestrate=True，Orchestrator 通过统一接口调用。
"""

from __future__ import annotations

import logging
from typing import Any

from pydantic import BaseModel

from ai_parenting.skills.base import BoundaryRule, Skill, SkillMetadata, SkillResult

logger = logging.getLogger(__name__)


class WeeklyFeedbackAdapter(Skill):
    """周反馈技能适配器。

    包装 renderer_weekly_feedback.py 的函数为统一的 Skill 接口。
    """

    @property
    def metadata(self) -> SkillMetadata:
        return SkillMetadata(
            name="weekly_feedback",
            display_name="周反馈",
            description="每周成长分析报告，总结训练进展",
            version="1.0.0",
            icon="📊",
            tags=["feedback", "report", "反馈", "总结", "报告"],
            session_type="weekly_feedback",
        )

    @property
    def supports_orchestrate(self) -> bool:
        return True

    def get_timeout_config(self) -> tuple[float, float]:
        return (20.0, 35.0)

    # ------------------------------------------------------------------
    # Orchestrator 模式方法
    # ------------------------------------------------------------------

    def render_prompt(self, context: Any, **kwargs: Any) -> str:
        from ai_parenting.renderer_weekly_feedback import render_weekly_feedback_prompt

        return render_weekly_feedback_prompt(
            context=context,
            child_nickname=kwargs.get("child_nickname", ""),
            active_plan_title=kwargs.get("active_plan_title", ""),
            active_plan_focus_theme=kwargs.get("active_plan_focus_theme", ""),
            plan_completion_rate=kwargs.get("plan_completion_rate", ""),
            record_count_this_week=kwargs.get("record_count_this_week", 0),
            day_tasks_summary=kwargs.get("day_tasks_summary", ""),
            weekly_records_detail=kwargs.get("weekly_records_detail", ""),
            active_plan_id=kwargs.get("active_plan_id", ""),
        )

    def parse_result(self, raw_json: str) -> BaseModel:
        from ai_parenting.renderer_weekly_feedback import parse_weekly_feedback_result

        return parse_weekly_feedback_result(raw_json)

    def check_boundary(self, result: BaseModel) -> Any:
        from ai_parenting.renderer_weekly_feedback import check_feedback_boundary

        return check_feedback_boundary(result)  # type: ignore[arg-type]

    def get_degraded_result(self) -> BaseModel:
        from ai_parenting.renderer_weekly_feedback import get_degraded_feedback_result

        return get_degraded_feedback_result()

    def get_template_version(self) -> str:
        from ai_parenting.renderer_weekly_feedback import get_feedback_template_version

        return get_feedback_template_version()

    # ------------------------------------------------------------------
    # 简单模式
    # ------------------------------------------------------------------

    async def execute(self, params: dict[str, Any], context: Any) -> SkillResult:
        """执行周反馈生成。"""
        try:
            from ai_parenting.renderer_weekly_feedback import (
                check_feedback_boundary,
                get_degraded_feedback_result,
                parse_weekly_feedback_result,
                render_weekly_feedback_prompt,
            )
            from ai_parenting.providers.base import ModelProvider

            prompt = render_weekly_feedback_prompt(
                context=context,
                child_nickname=params.get("child_nickname", ""),
                active_plan_title=params.get("active_plan_title", ""),
                active_plan_focus_theme=params.get("active_plan_focus_theme", ""),
                plan_completion_rate=params.get("plan_completion_rate", ""),
                record_count_this_week=params.get("record_count_this_week", 0),
                day_tasks_summary=params.get("day_tasks_summary", ""),
                weekly_records_detail=params.get("weekly_records_detail", ""),
                active_plan_id=params.get("active_plan_id", ""),
            )

            provider: ModelProvider | None = params.get("_provider")
            if provider is None:
                degraded = get_degraded_feedback_result()
                return SkillResult(
                    response_text="已生成本周反馈报告（备用版本）。",
                    structured_data=degraded,
                    boundary_passed=True,
                    is_degraded=True,
                )

            raw_json = await provider.generate(prompt)
            result = parse_weekly_feedback_result(raw_json)

            boundary_output = check_feedback_boundary(result)
            if boundary_output.cleaned_result:
                result = boundary_output.cleaned_result

            summary = result.summary_text if hasattr(result, "summary_text") and result.summary_text else "本周反馈已生成"

            return SkillResult(
                response_text=summary,
                structured_data=result,
                boundary_passed=boundary_output.passed,
                metadata={"flags_count": len(boundary_output.flags)},
            )

        except Exception as exc:
            logger.error("WeeklyFeedbackAdapter execute failed: %s", exc)
            try:
                from ai_parenting.renderer_weekly_feedback import get_degraded_feedback_result
                degraded = get_degraded_feedback_result()
                return SkillResult(
                    response_text="周反馈生成遇到问题，已使用备用方案。",
                    structured_data=degraded,
                    boundary_passed=True,
                    is_degraded=True,
                    metadata={"error": str(exc)},
                )
            except Exception:
                return SkillResult(
                    response_text="周反馈暂时不可用，请稍后再试。",
                    boundary_passed=True,
                    is_degraded=True,
                    metadata={"error": str(exc)},
                )

    def get_boundary_rules(self) -> list[BoundaryRule]:
        return [
            BoundaryRule(
                category="diagnosis_label",
                description="禁止在周反馈中出现医学诊断标签",
            ),
            BoundaryRule(
                category="blame_parent",
                description="禁止责备家长的表述",
            ),
            BoundaryRule(
                category="negate_child",
                description="禁止否定儿童的表述",
            ),
            BoundaryRule(
                category="overquantify",
                description="禁止过度量化儿童发展",
            ),
        ]
