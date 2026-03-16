"""统一编排调度器。

实现 AI 编排层的核心调度逻辑：
1. 根据 session_type 选择渲染器，渲染 Prompt
2. 调用 ModelProvider.generate()，含超时控制
3. 解析 JSON → 对应 Result 模型
4. 字段约束校验（Pydantic 自动完成）
5. 边界检查（BoundaryChecker）
6. 异常处理：超时 → 降级；解析失败 → 重试1次 → 降级；边界不通过 → 替换后返回
7. 构建 OutputMetadata，返回 OrchestrateResult
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

from pydantic import BaseModel, ValidationError

from ai_parenting.engine.boundary_checker import BoundaryChecker, BoundaryCheckOutput
from ai_parenting.models.enums import SessionStatus, SessionType
from ai_parenting.models.schemas import (
    ContextSnapshot,
    InstantHelpResult,
    OutputMetadata,
    PlanGenerationResult,
    WeeklyFeedbackResult,
)
from ai_parenting.providers.base import ModelProvider

# 渲染器导入
from ai_parenting.renderer import (
    check_boundary as check_instant_help_boundary,
    get_degraded_result as get_degraded_instant_help,
    get_template_version as get_instant_help_version,
    parse_instant_help_result,
    render_instant_help_prompt,
)
from ai_parenting.renderer_plan_generation import (
    check_plan_boundary,
    get_degraded_plan_result,
    get_plan_template_version,
    parse_plan_generation_result,
    render_plan_generation_prompt,
)
from ai_parenting.renderer_weekly_feedback import (
    check_feedback_boundary,
    get_degraded_feedback_result,
    get_feedback_template_version,
    parse_weekly_feedback_result,
    render_weekly_feedback_prompt,
)


# ---------------------------------------------------------------------------
# 超时配置
# ---------------------------------------------------------------------------

_TIMEOUT_CONFIG: dict[SessionType, float] = {
    SessionType.INSTANT_HELP: 8.0,
    SessionType.PLAN_GENERATION: 30.0,
    SessionType.WEEKLY_FEEDBACK: 20.0,
}

_FINAL_TIMEOUT_CONFIG: dict[SessionType, float] = {
    SessionType.INSTANT_HELP: 12.0,
    SessionType.PLAN_GENERATION: 45.0,
    SessionType.WEEKLY_FEEDBACK: 35.0,
}

# ---------------------------------------------------------------------------
# 编排结果
# ---------------------------------------------------------------------------


@dataclass
class OrchestrateResult:
    """编排调度结果。"""

    result: BaseModel  # InstantHelpResult | PlanGenerationResult | WeeklyFeedbackResult
    metadata: OutputMetadata
    status: SessionStatus


# ---------------------------------------------------------------------------
# 编排调度器
# ---------------------------------------------------------------------------


class Orchestrator:
    """统一编排调度器。

    统一处理三种 session_type 的 AI 调用流程：
    渲染 Prompt → 调用模型 → 解析 → 校验 → 边界检查 → 降级兜底。

    Args:
        provider: 模型供应商实现。

    用法::

        orchestrator = Orchestrator(provider)
        result = await orchestrator.orchestrate(
            session_type=SessionType.INSTANT_HELP,
            context=context_snapshot,
            user_scenario="吃饭不坐",
            user_input_text="孩子一直站着吃饭",
        )
    """

    def __init__(self, provider: ModelProvider) -> None:
        self._provider = provider
        self._boundary_checker = BoundaryChecker()

    async def orchestrate(
        self,
        session_type: SessionType,
        context: ContextSnapshot,
        **kwargs: Any,
    ) -> OrchestrateResult:
        """统一编排入口。

        Args:
            session_type: AI 会话类型。
            context: 儿童上下文快照。
            **kwargs: 各 session_type 专属参数：
                - instant_help: user_scenario, user_input_text, child_nickname,
                                active_plan_title, recent_records_summary
                - plan_generation: child_nickname, recent_records_summary
                - weekly_feedback: child_nickname, active_plan_title,
                                   active_plan_focus_theme, plan_completion_rate,
                                   record_count_this_week, day_tasks_summary,
                                   weekly_records_detail, active_plan_id

        Returns:
            OrchestrateResult，包含 result、metadata 和 status。
        """
        start_time = time.monotonic()
        timeout = _TIMEOUT_CONFIG[session_type]
        template_version = self._get_template_version(session_type)

        # Step 1: 渲染 Prompt
        prompt = self._render_prompt(session_type, context, **kwargs)

        # Step 2-6: 调用模型 + 解析 + 校验 + 边界检查（含重试和降级）
        result: BaseModel | None = None
        status = SessionStatus.COMPLETED
        boundary_passed = True
        boundary_flags: list[str] = []
        is_degraded = False

        for attempt in range(2):  # 最多 2 次（首次 + 1 次重试）
            try:
                # 调用模型
                raw_response = await asyncio.wait_for(
                    self._provider.generate(prompt, timeout),
                    timeout=timeout,
                )

                # 解析 + Pydantic 校验
                parsed = self._parse_result(session_type, raw_response)

                # 边界检查
                check_output = self._check_boundary(session_type, parsed)
                if check_output.passed:
                    result = parsed
                    boundary_passed = True
                else:
                    # 边界不通过 → 使用清洁后的结果
                    boundary_passed = False
                    boundary_flags = [f.category for f in check_output.flags]
                    result = check_output.cleaned_result if check_output.cleaned_result else parsed

                break  # 成功，跳出重试循环

            except asyncio.TimeoutError:
                if attempt == 0:
                    # 首次超时，使用更长的最终超时重试
                    timeout = _FINAL_TIMEOUT_CONFIG[session_type] - timeout
                    if timeout <= 0:
                        # 无法重试，直接降级
                        result = self._get_degraded_result(session_type)
                        status = SessionStatus.DEGRADED
                        is_degraded = True
                        break
                    continue
                else:
                    # 重试后仍超时，降级
                    result = self._get_degraded_result(session_type)
                    status = SessionStatus.DEGRADED
                    is_degraded = True
                    break

            except (ValidationError, ValueError, Exception) as e:
                if attempt == 0:
                    continue  # 首次失败，重试
                else:
                    # 重试后仍失败，降级
                    result = self._get_degraded_result(session_type)
                    status = SessionStatus.DEGRADED
                    is_degraded = True
                    break

        # 最终兜底（理论上不应该到达这里）
        if result is None:
            result = self._get_degraded_result(session_type)
            status = SessionStatus.DEGRADED
            is_degraded = True

        elapsed_ms = int((time.monotonic() - start_time) * 1000)

        metadata = OutputMetadata(
            prompt_template_version=template_version,
            model_provider=self._provider.provider_name,
            model_version=self._provider.model_version,
            boundary_check_passed=boundary_passed,
            boundary_check_flags=boundary_flags,
            generation_timestamp=datetime.now(timezone.utc),
            latency_ms=elapsed_ms,
        )

        return OrchestrateResult(
            result=result,
            metadata=metadata,
            status=status,
        )

    # ------------------------------------------------------------------
    # 内部方法：渲染 Prompt
    # ------------------------------------------------------------------

    def _render_prompt(
        self,
        session_type: SessionType,
        context: ContextSnapshot,
        **kwargs: Any,
    ) -> str:
        """根据 session_type 选择渲染器并渲染 Prompt。"""
        if session_type == SessionType.INSTANT_HELP:
            return render_instant_help_prompt(
                context=context,
                user_scenario=kwargs.get("user_scenario", ""),
                user_input_text=kwargs.get("user_input_text", ""),
                child_nickname=kwargs.get("child_nickname", ""),
                active_plan_title=kwargs.get("active_plan_title", ""),
                recent_records_summary=kwargs.get("recent_records_summary", ""),
            )
        elif session_type == SessionType.PLAN_GENERATION:
            return render_plan_generation_prompt(
                context=context,
                child_nickname=kwargs.get("child_nickname", ""),
                recent_records_summary=kwargs.get("recent_records_summary", ""),
            )
        elif session_type == SessionType.WEEKLY_FEEDBACK:
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
        else:
            raise ValueError(f"不支持的 session_type: {session_type}")

    # ------------------------------------------------------------------
    # 内部方法：解析 Result
    # ------------------------------------------------------------------

    def _parse_result(
        self,
        session_type: SessionType,
        raw_json: str,
    ) -> BaseModel:
        """根据 session_type 解析 JSON 为对应的 Result 类型。"""
        if session_type == SessionType.INSTANT_HELP:
            return parse_instant_help_result(raw_json)
        elif session_type == SessionType.PLAN_GENERATION:
            return parse_plan_generation_result(raw_json)
        elif session_type == SessionType.WEEKLY_FEEDBACK:
            return parse_weekly_feedback_result(raw_json)
        else:
            raise ValueError(f"不支持的 session_type: {session_type}")

    # ------------------------------------------------------------------
    # 内部方法：边界检查
    # ------------------------------------------------------------------

    def _check_boundary(
        self,
        session_type: SessionType,
        result: BaseModel,
    ) -> BoundaryCheckOutput:
        """根据 session_type 执行边界检查。"""
        if session_type == SessionType.INSTANT_HELP:
            return check_instant_help_boundary(result)  # type: ignore
        elif session_type == SessionType.PLAN_GENERATION:
            return check_plan_boundary(result)  # type: ignore
        elif session_type == SessionType.WEEKLY_FEEDBACK:
            return check_feedback_boundary(result)  # type: ignore
        else:
            raise ValueError(f"不支持的 session_type: {session_type}")

    # ------------------------------------------------------------------
    # 内部方法：获取降级结果
    # ------------------------------------------------------------------

    def _get_degraded_result(self, session_type: SessionType) -> BaseModel:
        """根据 session_type 获取降级结果。"""
        if session_type == SessionType.INSTANT_HELP:
            return get_degraded_instant_help()
        elif session_type == SessionType.PLAN_GENERATION:
            return get_degraded_plan_result()
        elif session_type == SessionType.WEEKLY_FEEDBACK:
            return get_degraded_feedback_result()
        else:
            raise ValueError(f"不支持的 session_type: {session_type}")

    # ------------------------------------------------------------------
    # 内部方法：获取模板版本
    # ------------------------------------------------------------------

    def _get_template_version(self, session_type: SessionType) -> str:
        """根据 session_type 获取模板版本。"""
        if session_type == SessionType.INSTANT_HELP:
            return get_instant_help_version()
        elif session_type == SessionType.PLAN_GENERATION:
            return get_plan_template_version()
        elif session_type == SessionType.WEEKLY_FEEDBACK:
            return get_feedback_template_version()
        else:
            raise ValueError(f"不支持的 session_type: {session_type}")
