"""统一编排调度器。

Phase 3 升级：
- 注入 SkillRegistry，通过 Skill 接口动态路由（替代硬编码的 if session_type == 分支）
- 保留向后兼容：无 SkillRegistry 时降级为直接导入 Renderer（Legacy 模式）
- Skill.supports_orchestrate=True 的技能由 Orchestrator 驱动：
    render_prompt → 调用模型 → parse_result → check_boundary
- 新增技能只需实现 Skill 接口并注册到 SkillRegistry，无需修改此文件

实现 AI 编排层的核心调度逻辑：
1. 根据 session_type 从 SkillRegistry 获取 Skill
2. 调用 Skill.render_prompt() 渲染 Prompt
3. 调用 ModelProvider.generate()，含超时控制
4. 调用 Skill.parse_result() 解析 JSON → Result 模型
5. 调用 Skill.check_boundary() 安全边界检查
6. 异常处理：超时 → 降级；解析失败 → 重试1次 → 降级；边界不通过 → 替换后返回
7. 构建 OutputMetadata，返回 OrchestrateResult
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Optional

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

if TYPE_CHECKING:
    from ai_parenting.skills.base import Skill
    from ai_parenting.skills.registry import SkillRegistry

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Legacy 渲染器导入（向后兼容，无 SkillRegistry 时降级使用）
# ---------------------------------------------------------------------------

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
# Legacy 超时配置（无 SkillRegistry 时使用）
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

    Phase 3 升级：
    - 支持两种模式：SkillRegistry 模式（推荐）和 Legacy 模式（向后兼容）
    - SkillRegistry 模式下，所有路由逻辑由 SkillRegistry 和 Skill 接口驱动
    - 新增技能无需修改此文件，只需注册到 SkillRegistry

    Args:
        provider: 模型供应商实现。
        skill_registry: 技能注册表（可选，为 None 时降级为 Legacy 模式）。

    用法::

        # Phase 3: SkillRegistry 模式（推荐）
        registry = SkillRegistry()
        registry.discover_and_register(adapters_path)
        orchestrator = Orchestrator(provider, skill_registry=registry)

        # Legacy: 直接调用（向后兼容）
        orchestrator = Orchestrator(provider)

        result = await orchestrator.orchestrate(
            session_type=SessionType.INSTANT_HELP,
            context=context_snapshot,
            user_scenario="吃饭不坐",
        )
    """

    def __init__(
        self,
        provider: ModelProvider,
        skill_registry: "SkillRegistry | None" = None,
    ) -> None:
        self._provider = provider
        self._skill_registry = skill_registry
        self._boundary_checker = BoundaryChecker()

    @property
    def skill_registry(self) -> "SkillRegistry | None":
        """获取注入的 SkillRegistry（供外部查询使用）。"""
        return self._skill_registry

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
            **kwargs: 各 session_type 专属参数。

        Returns:
            OrchestrateResult，包含 result、metadata 和 status。
        """
        # Phase 3: 优先通过 SkillRegistry 路由
        skill = self._resolve_skill(session_type)
        if skill is not None and skill.supports_orchestrate:
            return await self._orchestrate_via_skill(skill, context, **kwargs)

        # Legacy 降级：直接调用渲染器
        logger.debug(
            "Orchestrator falling back to legacy mode for session_type=%s",
            session_type.value,
        )
        return await self._orchestrate_legacy(session_type, context, **kwargs)

    def _resolve_skill(self, session_type: SessionType) -> "Skill | None":
        """从 SkillRegistry 按 session_type 查找对应的 Skill。"""
        if self._skill_registry is None:
            return None

        # 方式 1: 按 session_type.value 精确匹配 skill.metadata.session_type
        for skill in self._skill_registry.get_enabled_skills():
            if skill.metadata.session_type == session_type.value:
                return skill

        # 方式 2: 按名称匹配（session_type.value 与 skill name 相同）
        return self._skill_registry.get(session_type.value)

    # ==================================================================
    # Phase 3: SkillRegistry 模式
    # ==================================================================

    async def _orchestrate_via_skill(
        self,
        skill: "Skill",
        context: ContextSnapshot,
        **kwargs: Any,
    ) -> OrchestrateResult:
        """通过 Skill 接口驱动完整的编排流程。"""
        start_time = time.monotonic()
        initial_timeout, final_timeout = skill.get_timeout_config()
        template_version = skill.get_template_version()

        # Step 1: 渲染 Prompt
        prompt = skill.render_prompt(context, **kwargs)

        # Step 2-6: 调用模型 + 解析 + 校验 + 边界检查（含重试和降级）
        result: BaseModel | None = None
        status = SessionStatus.COMPLETED
        boundary_passed = True
        boundary_flags: list[str] = []
        is_degraded = False

        timeout = initial_timeout
        for attempt in range(2):  # 最多 2 次（首次 + 1 次重试）
            try:
                # 调用模型
                raw_response = await asyncio.wait_for(
                    self._provider.generate(prompt, timeout),
                    timeout=timeout,
                )

                # 解析 + Pydantic 校验
                parsed = skill.parse_result(raw_response)

                # 边界检查
                check_output = skill.check_boundary(parsed)
                if check_output.passed:
                    result = parsed
                    boundary_passed = True
                else:
                    boundary_passed = False
                    boundary_flags = [f.category for f in check_output.flags]
                    result = check_output.cleaned_result if check_output.cleaned_result else parsed

                break  # 成功

            except asyncio.TimeoutError:
                if attempt == 0:
                    timeout = final_timeout - initial_timeout
                    if timeout <= 0:
                        result = skill.get_degraded_result()
                        status = SessionStatus.DEGRADED
                        is_degraded = True
                        break
                    continue
                else:
                    result = skill.get_degraded_result()
                    status = SessionStatus.DEGRADED
                    is_degraded = True
                    break

            except (ValidationError, ValueError, Exception) as e:
                logger.warning(
                    "Skill '%s' orchestrate attempt %d failed: %s",
                    skill.metadata.name, attempt + 1, e,
                )
                if attempt == 0:
                    continue
                else:
                    result = skill.get_degraded_result()
                    status = SessionStatus.DEGRADED
                    is_degraded = True
                    break

        # 最终兜底
        if result is None:
            result = skill.get_degraded_result()
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

        logger.info(
            "Orchestrate via skill '%s': status=%s, latency=%dms, degraded=%s",
            skill.metadata.name, status.value, elapsed_ms, is_degraded,
        )

        return OrchestrateResult(
            result=result,
            metadata=metadata,
            status=status,
        )

    # ==================================================================
    # Legacy 模式（向后兼容，无 SkillRegistry 时使用）
    # ==================================================================

    async def _orchestrate_legacy(
        self,
        session_type: SessionType,
        context: ContextSnapshot,
        **kwargs: Any,
    ) -> OrchestrateResult:
        """Legacy 模式：直接调用渲染器函数。"""
        start_time = time.monotonic()
        timeout = _TIMEOUT_CONFIG[session_type]
        template_version = self._get_template_version_legacy(session_type)

        prompt = self._render_prompt_legacy(session_type, context, **kwargs)

        result: BaseModel | None = None
        status = SessionStatus.COMPLETED
        boundary_passed = True
        boundary_flags: list[str] = []
        is_degraded = False

        for attempt in range(2):
            try:
                raw_response = await asyncio.wait_for(
                    self._provider.generate(prompt, timeout),
                    timeout=timeout,
                )
                parsed = self._parse_result_legacy(session_type, raw_response)
                check_output = self._check_boundary_legacy(session_type, parsed)
                if check_output.passed:
                    result = parsed
                    boundary_passed = True
                else:
                    boundary_passed = False
                    boundary_flags = [f.category for f in check_output.flags]
                    result = check_output.cleaned_result if check_output.cleaned_result else parsed
                break

            except asyncio.TimeoutError:
                if attempt == 0:
                    timeout = _FINAL_TIMEOUT_CONFIG[session_type] - timeout
                    if timeout <= 0:
                        result = self._get_degraded_result_legacy(session_type)
                        status = SessionStatus.DEGRADED
                        is_degraded = True
                        break
                    continue
                else:
                    result = self._get_degraded_result_legacy(session_type)
                    status = SessionStatus.DEGRADED
                    is_degraded = True
                    break

            except (ValidationError, ValueError, Exception) as e:
                if attempt == 0:
                    continue
                else:
                    result = self._get_degraded_result_legacy(session_type)
                    status = SessionStatus.DEGRADED
                    is_degraded = True
                    break

        if result is None:
            result = self._get_degraded_result_legacy(session_type)
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
    # Legacy 内部方法
    # ------------------------------------------------------------------

    def _render_prompt_legacy(
        self, session_type: SessionType, context: ContextSnapshot, **kwargs: Any,
    ) -> str:
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

    def _parse_result_legacy(self, session_type: SessionType, raw_json: str) -> BaseModel:
        if session_type == SessionType.INSTANT_HELP:
            return parse_instant_help_result(raw_json)
        elif session_type == SessionType.PLAN_GENERATION:
            return parse_plan_generation_result(raw_json)
        elif session_type == SessionType.WEEKLY_FEEDBACK:
            return parse_weekly_feedback_result(raw_json)
        else:
            raise ValueError(f"不支持的 session_type: {session_type}")

    def _check_boundary_legacy(self, session_type: SessionType, result: BaseModel) -> BoundaryCheckOutput:
        if session_type == SessionType.INSTANT_HELP:
            return check_instant_help_boundary(result)  # type: ignore
        elif session_type == SessionType.PLAN_GENERATION:
            return check_plan_boundary(result)  # type: ignore
        elif session_type == SessionType.WEEKLY_FEEDBACK:
            return check_feedback_boundary(result)  # type: ignore
        else:
            raise ValueError(f"不支持的 session_type: {session_type}")

    def _get_degraded_result_legacy(self, session_type: SessionType) -> BaseModel:
        if session_type == SessionType.INSTANT_HELP:
            return get_degraded_instant_help()
        elif session_type == SessionType.PLAN_GENERATION:
            return get_degraded_plan_result()
        elif session_type == SessionType.WEEKLY_FEEDBACK:
            return get_degraded_feedback_result()
        else:
            raise ValueError(f"不支持的 session_type: {session_type}")

    def _get_template_version_legacy(self, session_type: SessionType) -> str:
        if session_type == SessionType.INSTANT_HELP:
            return get_instant_help_version()
        elif session_type == SessionType.PLAN_GENERATION:
            return get_plan_template_version()
        elif session_type == SessionType.WEEKLY_FEEDBACK:
            return get_feedback_template_version()
        else:
            raise ValueError(f"不支持的 session_type: {session_type}")
