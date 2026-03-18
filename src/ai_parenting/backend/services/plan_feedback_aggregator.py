"""微计划反馈数据聚合器。

聚合上一轮计划的执行数据，输出结构化的 PlanFeedbackContext，
供 plan_generation 渲染器注入 Prompt 上下文，实现大模型驱动的个性化微计划生成。

数据来源：
- Plan + DayTask：完成率、每日完成状态
- WeeklyFeedback：周反馈决策方向
- Record：本周观察记录中的关键趋势词
- Child：家长困扰度变化（通过 risk_level 推断）
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ai_parenting.backend.models import (
    Child,
    DayTask,
    Plan,
    Record,
    WeeklyFeedback,
)
from ai_parenting.models.enums import CompletionStatus, FeedbackStatus

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# 反馈上下文数据模型
# ---------------------------------------------------------------------------


class DayCompletionSummary(BaseModel):
    """单日完成情况摘要。"""

    day_number: int = Field(..., ge=1, le=7, description="日序号")
    status: str = Field(..., description="完成状态")
    main_exercise_title: str = Field(default="", description="主练习标题")


class PlanFeedbackContext(BaseModel):
    """计划反馈上下文 — 供 Prompt 渲染器注入。

    当没有上一轮计划数据时，所有字段使用默认值，
    渲染器可通过 has_previous_plan 判断是否注入反馈段。
    """

    has_previous_plan: bool = Field(
        default=False,
        description="是否存在上一轮已完成的计划",
    )

    # —— 计划执行数据 ——
    previous_plan_title: str = Field(default="", description="上一轮计划标题")
    previous_focus_theme: str = Field(default="", description="上一轮焦点主题")
    completion_rate: float = Field(
        default=0.0, ge=0.0, le=1.0, description="上一轮计划完成率"
    )
    day_completions: list[DayCompletionSummary] = Field(
        default_factory=list,
        description="每日完成状态摘要",
    )
    executed_days: int = Field(default=0, description="实际执行天数")
    partial_days: int = Field(default=0, description="部分完成天数")
    skipped_days: int = Field(default=0, description="未执行天数")

    # —— 周反馈决策 ——
    feedback_decision: Optional[str] = Field(
        None,
        description="家长选择的下周方向（continue/lower_difficulty/change_focus）",
    )
    feedback_summary: Optional[str] = Field(
        None,
        description="周反馈摘要文本",
    )
    positive_changes_count: int = Field(
        default=0, description="识别到的积极变化数"
    )
    opportunities_count: int = Field(
        default=0, description="仍需机会数"
    )

    # —— 观察记录趋势 ——
    record_count_this_week: int = Field(
        default=0, description="本周观察记录数"
    )
    trend_keywords: list[str] = Field(
        default_factory=list,
        description="本周记录关键趋势词（最多 10 个）",
    )
    most_frequent_scenes: list[str] = Field(
        default_factory=list,
        description="最高频的记录场景（最多 3 个）",
    )

    # —— 风险变化 ——
    risk_level_changed: bool = Field(
        default=False, description="风险层级是否发生变化"
    )
    previous_risk_level: Optional[str] = Field(
        None, description="上一轮计划创建时的风险层级"
    )
    current_risk_level: Optional[str] = Field(
        None, description="当前风险层级"
    )

    # —— 家长笔记 ——
    next_week_context: Optional[str] = Field(
        None, description="家长追加的关注内容"
    )


# ---------------------------------------------------------------------------
# 聚合函数
# ---------------------------------------------------------------------------


async def aggregate_plan_feedback(
    db: AsyncSession,
    child_id: uuid.UUID,
) -> PlanFeedbackContext:
    """聚合指定儿童上一轮已完成计划的反馈数据。

    查询逻辑：
    1. 查找最近一个 completed/superseded 状态的 Plan
    2. 统计 DayTask 完成情况
    3. 查找对应的 WeeklyFeedback 决策
    4. 聚合同期 Record 的关键词和场景
    5. 比对 risk_level 变化

    Args:
        db: 异步数据库会话。
        child_id: 儿童 ID。

    Returns:
        PlanFeedbackContext 实例，即使无数据也返回默认空上下文。
    """
    context = PlanFeedbackContext()

    # 1. 查找最近一个已完成的计划
    result = await db.execute(
        select(Plan)
        .where(
            Plan.child_id == child_id,
            Plan.status.in_(["completed", "superseded"]),
        )
        .order_by(Plan.created_at.desc())
        .limit(1)
    )
    prev_plan = result.scalar_one_or_none()

    if prev_plan is None:
        return context

    context.has_previous_plan = True
    context.previous_plan_title = prev_plan.title
    context.previous_focus_theme = prev_plan.focus_theme
    context.completion_rate = prev_plan.completion_rate
    context.previous_risk_level = prev_plan.risk_level_at_creation
    context.next_week_context = prev_plan.next_week_context

    # 2. 统计 DayTask 完成情况
    day_completions = []
    executed = 0
    partial = 0
    skipped = 0

    for task in prev_plan.day_tasks:
        day_completions.append(
            DayCompletionSummary(
                day_number=task.day_number,
                status=task.completion_status,
                main_exercise_title=task.main_exercise_title,
            )
        )
        if task.completion_status == CompletionStatus.EXECUTED.value:
            executed += 1
        elif task.completion_status == CompletionStatus.PARTIAL.value:
            partial += 1
        else:
            skipped += 1

    context.day_completions = day_completions
    context.executed_days = executed
    context.partial_days = partial
    context.skipped_days = skipped

    # 3. 查找对应的 WeeklyFeedback
    fb_result = await db.execute(
        select(WeeklyFeedback)
        .where(
            WeeklyFeedback.plan_id == prev_plan.id,
            WeeklyFeedback.status.in_([
                FeedbackStatus.DECIDED.value,
                FeedbackStatus.VIEWED.value,
                FeedbackStatus.READY.value,
            ]),
        )
        .order_by(WeeklyFeedback.created_at.desc())
        .limit(1)
    )
    feedback = fb_result.scalar_one_or_none()

    if feedback is not None:
        context.feedback_decision = feedback.selected_decision
        context.feedback_summary = feedback.summary_text
        context.positive_changes_count = (
            len(feedback.positive_changes) if isinstance(feedback.positive_changes, list) else 0
        )
        context.opportunities_count = (
            len(feedback.opportunities) if isinstance(feedback.opportunities, list) else 0
        )

    # 4. 聚合同期 Record 的关键词和场景
    plan_start = datetime(
        prev_plan.start_date.year,
        prev_plan.start_date.month,
        prev_plan.start_date.day,
        tzinfo=timezone.utc,
    )
    plan_end = datetime(
        prev_plan.end_date.year,
        prev_plan.end_date.month,
        prev_plan.end_date.day,
        hour=23, minute=59, second=59,
        tzinfo=timezone.utc,
    )

    records_result = await db.execute(
        select(Record)
        .where(
            Record.child_id == child_id,
            Record.created_at >= plan_start,
            Record.created_at <= plan_end,
        )
        .order_by(Record.created_at.desc())
        .limit(50)
    )
    records = list(records_result.scalars().all())
    context.record_count_this_week = len(records)

    # 提取趋势关键词（从 tags 聚合）
    tag_counter: dict[str, int] = {}
    scene_counter: dict[str, int] = {}
    for record in records:
        if record.tags:
            for tag in record.tags:
                tag_counter[tag] = tag_counter.get(tag, 0) + 1
        if record.scene:
            scene_counter[record.scene] = scene_counter.get(record.scene, 0) + 1

    # 按频次降序取 top 10 关键词
    sorted_tags = sorted(tag_counter.items(), key=lambda x: x[1], reverse=True)
    context.trend_keywords = [tag for tag, _ in sorted_tags[:10]]

    # 按频次降序取 top 3 场景
    sorted_scenes = sorted(scene_counter.items(), key=lambda x: x[1], reverse=True)
    context.most_frequent_scenes = [scene for scene, _ in sorted_scenes[:3]]

    # 5. 比对风险层级变化
    child_result = await db.execute(
        select(Child).where(Child.id == child_id)
    )
    child = child_result.scalar_one_or_none()
    if child is not None:
        context.current_risk_level = child.risk_level
        context.risk_level_changed = (
            prev_plan.risk_level_at_creation != child.risk_level
        )

    logger.info(
        "Aggregated feedback for child=%s: prev_plan=%s, completion=%.0f%%, "
        "decision=%s, records=%d, risk_changed=%s",
        child_id,
        prev_plan.id,
        context.completion_rate * 100,
        context.feedback_decision,
        context.record_count_this_week,
        context.risk_level_changed,
    )

    return context


async def render_feedback_context_text(
    feedback_ctx: PlanFeedbackContext,
) -> str:
    """将 PlanFeedbackContext 渲染为可注入 Prompt 的自然语言文本。

    如果没有上一轮数据（has_previous_plan=False），返回空字符串。
    渲染器在拼接 Prompt 时检查此返回值，为空则跳过反馈段。

    Args:
        feedback_ctx: 聚合后的反馈上下文。

    Returns:
        可直接插入 Prompt 的文本段，或空字符串。
    """
    if not feedback_ctx.has_previous_plan:
        return ""

    lines = ["【上周计划执行反馈——请据此调整本周计划】", ""]

    # 执行概况
    lines.append(
        f"上周计划「{feedback_ctx.previous_plan_title}」"
        f"（焦点：{feedback_ctx.previous_focus_theme}），"
        f"完成率 {feedback_ctx.completion_rate * 100:.0f}%"
        f"（完成 {feedback_ctx.executed_days} 天、"
        f"部分完成 {feedback_ctx.partial_days} 天、"
        f"未执行 {feedback_ctx.skipped_days} 天）。"
    )

    # 家长决策
    if feedback_ctx.feedback_decision:
        decision_map = {
            "continue": "继续同焦点巩固",
            "lower_difficulty": "降低难度",
            "change_focus": "切换焦点",
        }
        decision_text = decision_map.get(
            feedback_ctx.feedback_decision, feedback_ctx.feedback_decision
        )
        lines.append(f"家长选择的下周方向：{decision_text}。")

    # 周反馈摘要
    if feedback_ctx.feedback_summary:
        lines.append(f"周反馈摘要：{feedback_ctx.feedback_summary[:200]}")

    # 观察记录趋势
    if feedback_ctx.record_count_this_week > 0:
        lines.append(
            f"本周共 {feedback_ctx.record_count_this_week} 条观察记录。"
        )
        if feedback_ctx.trend_keywords:
            lines.append(
                f"高频关键词：{', '.join(feedback_ctx.trend_keywords[:5])}。"
            )
        if feedback_ctx.most_frequent_scenes:
            lines.append(
                f"高频场景：{', '.join(feedback_ctx.most_frequent_scenes)}。"
            )

    # 风险变化
    if feedback_ctx.risk_level_changed:
        lines.append(
            f"⚠️ 风险层级变化：{feedback_ctx.previous_risk_level} → "
            f"{feedback_ctx.current_risk_level}。请据此调整计划强度和语气。"
        )

    # 家长笔记
    if feedback_ctx.next_week_context:
        lines.append(
            f"家长补充关注：{feedback_ctx.next_week_context[:150]}"
        )

    # 调整指令
    lines.append("")
    lines.append("请根据以上反馈数据调整本周计划：")

    if feedback_ctx.feedback_decision == "continue":
        lines.append("- 保持同一焦点，但在上周最薄弱的环节加强支持")
        lines.append("- 保留上周最有效的场景和话术，微调未完成天的任务难度")
    elif feedback_ctx.feedback_decision == "lower_difficulty":
        lines.append("- 降低任务难度：减少互动回合数、缩短练习时长、简化话术")
        lines.append("- 优先保留上周完成率最高的场景")
        lines.append("- Day 1-3 只做最基础动作，Day 4 之后再视情况微调")
    elif feedback_ctx.feedback_decision == "change_focus":
        lines.append("- 切换到新的焦点主题，但保留上周积累的有效互动习惯")
        lines.append("- 新焦点的 Day 1 从最简单的基线开始")
    else:
        lines.append("- 综合完成率和记录趋势，自动判断最合适的调整方向")

    if feedback_ctx.completion_rate < 0.3:
        lines.append("- 完成率偏低，请显著降低任务量和难度，每天只保留 1 个核心动作")
    elif feedback_ctx.completion_rate < 0.6:
        lines.append("- 完成率中等，请在保持节奏的基础上适当精简")

    return "\n".join(lines)
