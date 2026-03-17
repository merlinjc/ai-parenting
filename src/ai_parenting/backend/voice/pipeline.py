"""语音管线核心。

PipelineStage 链式处理架构：
  ASR 文本 → IntentClassifier → SkillRouter → TextResponse

iOS 原生优先策略下，管线精简为：
  接收文本（iOS ASR 已转写）→ 意图分类 → Skill 路由 → 返回文本（iOS TTS 播报）

Phase 2 升级：
  - 注入 AsyncSession，quick_record/query_plan 直接操作数据库
  - quick_record → record_service.create_record（type=voice）
  - query_plan → plan_service.get_active_plan + get_today_task
  - query_progress → record_service.get_streak_days + plan completion_rate
"""

from __future__ import annotations

import logging
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Generic, TypeVar

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

TInput = TypeVar("TInput")
TOutput = TypeVar("TOutput")


# ---------------------------------------------------------------------------
# PipelineStage 统一接口
# ---------------------------------------------------------------------------


class PipelineStage(ABC, Generic[TInput, TOutput]):
    """管线阶段抽象基类。

    每个 Stage 实现统一的 process 接口，
    支持后续插入中间件（如情感分析、语言检测）。
    """

    @abstractmethod
    async def process(self, input_data: TInput, context: dict[str, Any]) -> TOutput:
        """处理输入数据，返回输出数据。"""
        ...

    @property
    @abstractmethod
    def stage_name(self) -> str:
        """阶段名称，用于日志和监控。"""
        ...


# ---------------------------------------------------------------------------
# 数据模型
# ---------------------------------------------------------------------------


@dataclass
class IntentResult:
    """意图分类结果。"""

    intent: str  # 意图名称，如 "quick_record", "instant_help", "query_plan"
    confidence: float  # 置信度 0.0-1.0
    matched_by: str  # 匹配方式: "rule" | "llm"
    parameters: dict[str, Any] = field(default_factory=dict)  # 提取的参数


@dataclass
class PipelineResult:
    """管线完整结果。"""

    reply_text: str
    intent: str
    action_taken: dict[str, Any] | None = None
    should_fallback_to_cloud_asr: bool = False
    latency_ms: int = 0
    stages_timing: dict[str, int] = field(default_factory=dict)  # 各阶段耗时
    record_id: str | None = None  # 快速记录创建后返回的 record_id


# ---------------------------------------------------------------------------
# VoicePipeline
# ---------------------------------------------------------------------------


class VoicePipeline:
    """语音管线控制器。

    iOS 原生优先策略下的简化管线：
    1. 接收 iOS ASR 转写文本
    2. IntentClassifier 分类意图
    3. SkillRegistry 路由到对应 Skill / 内置快捷指令
    4. 返回纯文本回复（iOS 端 TTS 播报）

    Phase 2 升级：
    - 注入 AsyncSession 以支持数据库操作
    - quick_record 真实创建 Record（type=voice）
    - query_plan 真实查询活跃计划 + 今日任务
    - query_progress 查询连续打卡天数 + 完成率

    Usage:
        pipeline = VoicePipeline(intent_classifier, skill_registry)
        result = await pipeline.process_text(transcript, child_id, db=db, user_id=user_id)
    """

    def __init__(
        self,
        intent_classifier: "IntentClassifierStage",
        skill_registry: Any = None,
    ) -> None:
        self._intent_classifier = intent_classifier
        self._skill_registry = skill_registry

    async def process_text(
        self,
        transcript: str,
        child_id: str,
        context: Any = None,
        *,
        asr_confidence: float | None = None,
        db: "AsyncSession | None" = None,
        user_id: str | None = None,
    ) -> PipelineResult:
        """处理 ASR 转写文本，返回 AI 回复。

        Args:
            transcript: iOS 端 ASR 转写后的文本。
            child_id: 孩子 ID（用于 Skill 执行上下文）。
            context: 可选的 ContextSnapshot。
            asr_confidence: iOS 端 ASR 的置信度（用于判断是否建议降级到云端）。
            db: 数据库会话（Phase 2：用于 quick_record 入库和 query_plan 查询）。
            user_id: 当前用户 ID（Phase 2：用于 quick_record 关联用户）。

        Returns:
            PipelineResult，包含回复文本和意图信息。
        """
        pipeline_start = time.monotonic()
        stages_timing: dict[str, int] = {}

        # Stage 1: 意图分类
        stage_start = time.monotonic()
        intent_result = await self._intent_classifier.process(
            transcript,
            {"child_id": child_id},
        )
        stages_timing["intent_classify"] = int((time.monotonic() - stage_start) * 1000)

        logger.info(
            "Intent classified: intent=%s, confidence=%.2f, matched_by=%s",
            intent_result.intent, intent_result.confidence, intent_result.matched_by,
        )

        # Stage 2: Skill 路由
        stage_start = time.monotonic()
        reply_text, action_taken, record_id = await self._route_to_skill(
            intent_result, transcript, child_id, context, db=db, user_id=user_id,
        )
        stages_timing["skill_execute"] = int((time.monotonic() - stage_start) * 1000)

        total_ms = int((time.monotonic() - pipeline_start) * 1000)

        # 判断是否建议 iOS 端降级到云端 ASR
        should_fallback = False
        if asr_confidence is not None and asr_confidence < 0.6:
            should_fallback = True

        return PipelineResult(
            reply_text=reply_text,
            intent=intent_result.intent,
            action_taken=action_taken,
            should_fallback_to_cloud_asr=should_fallback,
            latency_ms=total_ms,
            stages_timing=stages_timing,
            record_id=record_id,
        )

    async def _route_to_skill(
        self,
        intent: IntentResult,
        transcript: str,
        child_id: str,
        context: Any,
        *,
        db: "AsyncSession | None" = None,
        user_id: str | None = None,
    ) -> tuple[str, dict[str, Any] | None, str | None]:
        """根据意图路由到对应 Skill 执行。

        Returns:
            (reply_text, action_taken, record_id)
        """
        # 快速指令：直接数据库操作，无需 AI
        if intent.intent == "quick_record":
            return await self._handle_quick_record(
                transcript, child_id, intent.parameters, db=db,
            )

        if intent.intent == "query_plan":
            return await self._handle_query_plan(child_id, db=db)

        if intent.intent == "query_progress":
            return await self._handle_query_progress(child_id, db=db)

        # 通过 SkillRegistry 路由（instant_help / weekly_feedback 等）
        if self._skill_registry:
            skill = self._skill_registry.match_by_intent(intent.intent)
            if skill:
                try:
                    result = await skill.execute(
                        params={
                            "user_input_text": transcript,
                            "user_scenario": f"voice:{intent.intent}",
                            **intent.parameters,
                        },
                        context=context,
                    )
                    return result.response_text, {"skill": skill.metadata.name}, None
                except Exception as exc:
                    logger.error("Skill execution failed: %s", exc)

        # 兜底：返回通用回复
        return (
            "我听到了您的话，但暂时不太确定您需要什么帮助。"
            "您可以试试说「记录」「今天做什么」或「这周完成多少」。",
            None,
            None,
        )

    # ------------------------------------------------------------------
    # 快捷指令实现（Phase 2：真实数据库操作）
    # ------------------------------------------------------------------

    async def _handle_quick_record(
        self,
        transcript: str,
        child_id: str,
        params: dict[str, Any],
        *,
        db: "AsyncSession | None" = None,
    ) -> tuple[str, dict[str, Any] | None, str | None]:
        """处理快速语音记录意图 — 创建观察记录入库。

        从语音转写中提取关键内容，创建 Record(type=voice)。
        """
        content = params.get("content", transcript)
        record_id: str | None = None

        if db is not None:
            try:
                from ai_parenting.backend.schemas import RecordCreate
                from ai_parenting.backend.services.record_service import create_record

                record_data = RecordCreate(
                    child_id=uuid.UUID(child_id),
                    type="voice",
                    content=content,
                    transcript=transcript,
                    tags=["语音记录"],
                    scene="voice_quick_record",
                )
                record = await create_record(db, record_data)
                await db.commit()
                record_id = str(record.id)
                logger.info(
                    "Voice quick_record created: record_id=%s, child=%s",
                    record_id, child_id,
                )
            except Exception as exc:
                logger.error("Failed to create voice record: %s", exc)
                await db.rollback()
                # 降级：不阻断回复，但告知用户记录可能未保存
                return (
                    f"语音已接收到「{content[:30]}{'...' if len(content) > 30 else ''}」，"
                    "但保存时遇到了问题，请稍后在 App 中手动添加。",
                    {"action": "record_failed", "child_id": child_id, "error": str(exc)},
                    None,
                )
        else:
            logger.warning("No db session for quick_record, skipping persistence")

        preview = content[:30] + ("..." if len(content) > 30 else "")
        return (
            f"已记录！「{preview}」",
            {
                "action": "record_created",
                "child_id": child_id,
                "content": content,
                "record_id": record_id,
            },
            record_id,
        )

    async def _handle_query_plan(
        self,
        child_id: str,
        *,
        db: "AsyncSession | None" = None,
    ) -> tuple[str, dict[str, Any] | None, str | None]:
        """处理查询今日计划意图 — 查询活跃计划及今日任务。"""
        if db is None:
            return "让我帮您查看今天的任务...（数据库未就绪）", None, None

        try:
            from ai_parenting.backend.services.plan_service import (
                get_active_plan,
                get_today_task,
            )

            plan = await get_active_plan(db, uuid.UUID(child_id))
            if plan is None:
                return (
                    "当前没有活跃的训练计划。您可以在 App 中创建新计划。",
                    {"action": "no_active_plan", "child_id": child_id},
                    None,
                )

            task = await get_today_task(db, plan)
            if task is None:
                return (
                    f"今天是计划「{plan.title}」的第 {plan.current_day} 天，"
                    "但暂时没有找到今日任务。",
                    {"action": "query_plan", "child_id": child_id, "plan_id": str(plan.id)},
                    None,
                )

            # 构建播报文本
            status_text = ""
            if task.completion_status == "executed":
                status_text = "✅ 今天已经完成了，真棒！"
            elif task.completion_status == "partial":
                status_text = "今天部分完成了，继续加油！"
            else:
                status_text = "还没开始，找机会试试吧！"

            reply = (
                f"今天是「{plan.title}」第 {plan.current_day} 天。"
                f"主题练习：{task.main_exercise_title}。"
                f"{task.main_exercise_description[:80]}。"
                f"{status_text}"
            )

            return (
                reply,
                {
                    "action": "query_plan",
                    "child_id": child_id,
                    "plan_id": str(plan.id),
                    "day_number": task.day_number,
                    "completion_status": task.completion_status,
                },
                None,
            )
        except Exception as exc:
            logger.error("Failed to query plan: %s", exc)
            return "查询今日计划时遇到了问题，请稍后再试。", None, None

    async def _handle_query_progress(
        self,
        child_id: str,
        *,
        db: "AsyncSession | None" = None,
    ) -> tuple[str, dict[str, Any] | None, str | None]:
        """处理进度查询意图 — 查询连续打卡天数和本周完成率。"""
        if db is None:
            return "让我查看一下您的进度...（数据库未就绪）", None, None

        try:
            from ai_parenting.backend.services.plan_service import get_active_plan
            from ai_parenting.backend.services.record_service import get_streak_days

            child_uuid = uuid.UUID(child_id)
            streak = await get_streak_days(db, child_uuid)
            plan = await get_active_plan(db, child_uuid)

            parts: list[str] = []

            if streak > 0:
                parts.append(f"您已经连续记录 {streak} 天了，非常棒！")
            else:
                parts.append("今天还没有记录，开始今天的记录吧！")

            if plan is not None:
                rate_pct = int(plan.completion_rate * 100)
                parts.append(
                    f"当前计划「{plan.title}」进行到第 {plan.current_day} 天，"
                    f"完成率 {rate_pct}%。"
                )

            return (
                "".join(parts),
                {
                    "action": "query_progress",
                    "child_id": child_id,
                    "streak_days": streak,
                    "completion_rate": plan.completion_rate if plan else None,
                },
                None,
            )
        except Exception as exc:
            logger.error("Failed to query progress: %s", exc)
            return "查询进度时遇到了问题，请稍后再试。", None, None


# 为 VoicePipeline 的类型提示
class IntentClassifierStage(PipelineStage[str, IntentResult]):
    """意图分类阶段的类型标注基类。"""

    @property
    def stage_name(self) -> str:
        return "intent_classifier"
