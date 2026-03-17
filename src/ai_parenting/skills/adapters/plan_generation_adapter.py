"""微计划生成 SkillAdapter。

将现有 renderer_plan_generation.py 包装为 Skill 接口。
Phase 3 升级：supports_orchestrate=True，Orchestrator 通过统一接口调用。
"""

from __future__ import annotations

import logging
from typing import Any

from pydantic import BaseModel

from ai_parenting.skills.base import BoundaryRule, Skill, SkillMetadata, SkillResult

logger = logging.getLogger(__name__)


class PlanGenerationAdapter(Skill):
    """微计划生成技能适配器。

    包装 renderer_plan_generation.py 的函数为统一的 Skill 接口。
    """

    @property
    def metadata(self) -> SkillMetadata:
        return SkillMetadata(
            name="plan_generation",
            display_name="微计划",
            description="生成 7 天个性化训练计划",
            version="1.0.0",
            icon="📋",
            tags=["plan", "计划", "训练", "安排"],
            session_type="plan_generation",
        )

    @property
    def supports_orchestrate(self) -> bool:
        return True

    def get_timeout_config(self) -> tuple[float, float]:
        return (30.0, 45.0)

    # ------------------------------------------------------------------
    # Orchestrator 模式方法
    # ------------------------------------------------------------------

    def render_prompt(self, context: Any, **kwargs: Any) -> str:
        from ai_parenting.renderer_plan_generation import render_plan_generation_prompt

        return render_plan_generation_prompt(
            context=context,
            child_nickname=kwargs.get("child_nickname", ""),
            recent_records_summary=kwargs.get("recent_records_summary", ""),
        )

    def parse_result(self, raw_json: str) -> BaseModel:
        from ai_parenting.renderer_plan_generation import parse_plan_generation_result

        return parse_plan_generation_result(raw_json)

    def check_boundary(self, result: BaseModel) -> Any:
        from ai_parenting.renderer_plan_generation import check_plan_boundary

        return check_plan_boundary(result)  # type: ignore[arg-type]

    def get_degraded_result(self) -> BaseModel:
        from ai_parenting.renderer_plan_generation import get_degraded_plan_result

        return get_degraded_plan_result()

    def get_template_version(self) -> str:
        from ai_parenting.renderer_plan_generation import get_plan_template_version

        return get_plan_template_version()

    # ------------------------------------------------------------------
    # 简单模式
    # ------------------------------------------------------------------

    async def execute(self, params: dict[str, Any], context: Any) -> SkillResult:
        """执行微计划生成。"""
        try:
            from ai_parenting.renderer_plan_generation import (
                check_plan_boundary,
                get_degraded_plan_result,
                parse_plan_generation_result,
                render_plan_generation_prompt,
            )
            from ai_parenting.providers.base import ModelProvider

            prompt = render_plan_generation_prompt(
                context=context,
                child_nickname=params.get("child_nickname", ""),
                recent_records_summary=params.get("recent_records_summary", ""),
            )

            provider: ModelProvider | None = params.get("_provider")
            if provider is None:
                degraded = get_degraded_plan_result()
                return SkillResult(
                    response_text=f"已生成微计划：{degraded.title}" if hasattr(degraded, "title") else str(degraded),
                    structured_data=degraded,
                    boundary_passed=True,
                    is_degraded=True,
                )

            raw_json = await provider.generate(prompt)
            result = parse_plan_generation_result(raw_json)

            boundary_output = check_plan_boundary(result)
            if boundary_output.cleaned_result:
                result = boundary_output.cleaned_result

            response_text = f"已生成微计划：{result.title}" if hasattr(result, "title") else str(result)

            return SkillResult(
                response_text=response_text,
                structured_data=result,
                boundary_passed=boundary_output.passed,
                metadata={"flags_count": len(boundary_output.flags)},
            )

        except Exception as exc:
            logger.error("PlanGenerationAdapter execute failed: %s", exc)
            try:
                from ai_parenting.renderer_plan_generation import get_degraded_plan_result
                degraded = get_degraded_plan_result()
                return SkillResult(
                    response_text="微计划生成遇到问题，已使用备用方案。",
                    structured_data=degraded,
                    boundary_passed=True,
                    is_degraded=True,
                    metadata={"error": str(exc)},
                )
            except Exception:
                return SkillResult(
                    response_text="微计划生成暂时不可用，请稍后再试。",
                    boundary_passed=True,
                    is_degraded=True,
                    metadata={"error": str(exc)},
                )

    def get_boundary_rules(self) -> list[BoundaryRule]:
        return [
            BoundaryRule(
                category="diagnosis_label",
                description="禁止在微计划中出现医学诊断标签",
            ),
            BoundaryRule(
                category="absolute_judgment",
                description="禁止使用绝对判断表述（如'一定会'、'绝对能'）",
            ),
            BoundaryRule(
                category="overquantify",
                description="禁止过度量化儿童发展（如具体百分位数等）",
            ),
            BoundaryRule(
                category="field_completeness",
                description="微计划必须包含完整的 7 天任务",
            ),
            BoundaryRule(
                category="field_length",
                description="任务描述和示范脚本字数限制检查",
            ),
        ]
