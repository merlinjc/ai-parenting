"""家长状态模型。

基于家长效能感（Parental Self-Efficacy）和养育压力（Parenting Stress）
的研究文献，定义家长状态数据结构，用于个性化调整计划和反馈的语气与密度。

理论来源：
- Jones & Prinz (2005): Parental self-efficacy as predictor of compliance
- Crnic & Low (2002): Everyday stresses and parenting
- Deater-Deckard (1998): Parenting stress and child adjustment
- Glascoe (2000): Parents' concerns as screening tool
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass
class ParentWellbeing:
    """家长当前状态快照。

    由上层服务根据家长行为信号（记录频率、文本情绪、完成率变化等）推断。
    不需要家长主动填写量表，通过行为信号间接建模。

    Attributes:
        efficacy_signal: 家长效能感信号（通过记录内容中的积极/消极自评推断）
        fatigue_signal: 疲劳信号（通过记录频率下降、文本简短化等推断）
        engagement_trend: 参与度趋势（通过近期记录频率和完成率推断）
        distress_weeks: 持续表达困扰的周数
        recent_positive_language: 近期记录中是否出现积极自评语言
        support_preference: 当前最适合的支持强度
    """

    efficacy_signal: Literal["confident", "neutral", "struggling"] = "neutral"
    fatigue_signal: Literal["energized", "normal", "fatigued", "burnout_risk"] = "normal"
    engagement_trend: Literal["increasing", "stable", "decreasing"] = "stable"
    distress_weeks: int = 0
    recent_positive_language: bool = False
    support_preference: Literal["full_plan", "light_plan", "pause_and_rest"] = "full_plan"

    @property
    def needs_extra_encouragement(self) -> bool:
        """是否需要在计划中增加额外鼓励。"""
        return (
            self.efficacy_signal == "struggling"
            or self.fatigue_signal in ("fatigued", "burnout_risk")
            or self.engagement_trend == "decreasing"
        )

    @property
    def should_reduce_task_density(self) -> bool:
        """是否应降低每日任务复杂度。"""
        return (
            self.fatigue_signal == "burnout_risk"
            or (self.fatigue_signal == "fatigued" and self.engagement_trend == "decreasing")
            or self.support_preference == "light_plan"
        )

    @property
    def should_suggest_pause(self) -> bool:
        """是否应建议暂停计划。"""
        return (
            self.support_preference == "pause_and_rest"
            or (self.fatigue_signal == "burnout_risk" and self.distress_weeks >= 3)
        )

    def get_plan_adaptation_hints(self) -> list[str]:
        """返回计划适配建议列表，供渲染器注入 Prompt。"""
        hints = []

        if self.should_suggest_pause:
            hints.append(
                "家长近期状态显示需要休息。请在 conservative_note 中明确传达"
                "'暂停计划不等于放弃，照顾好自己也是照顾孩子'的信息。"
                "本周计划应极度简化，每日只保留 1 个最小互动机会。"
            )
        elif self.should_reduce_task_density:
            hints.append(
                "家长近期疲劳度较高。请降低每日任务复杂度——"
                "main_exercise 和 natural_embed 的描述应更简短，"
                "demo_script 使用最短话术，observation_point 聚焦'家长做了什么'而非'孩子表现如何'。"
            )

        if self.needs_extra_encouragement:
            hints.append(
                "家长近期效能感较低。请在 observation_point 中至少包含 1 句"
                "肯定家长行动的表达（如'你今天花了时间陪伴，这本身就有意义'），"
                "weekend_review_prompt 中应突出家长的坚持和投入。"
            )

        if self.engagement_trend == "decreasing":
            hints.append(
                "家长记录频率在下降。请在 conservative_note 中传递"
                "'即使不记录，只要在日常中有一个小互动就够了'的信息，"
                "降低记录和打点的心理压力。"
            )

        if self.recent_positive_language:
            hints.append(
                "家长近期记录中出现了积极自评。请在计划中呼应这种积极体验，"
                "帮助家长看见自己做对了什么。"
            )

        return hints


def infer_wellbeing_from_signals(
    record_count_7d: int,
    record_count_prev_7d: int,
    plan_completion_rate: float,
    has_distress_language: bool,
    has_positive_language: bool,
    distress_weeks: int = 0,
) -> ParentWellbeing:
    """从行为信号推断家长状态。

    这是一个轻量级推断函数，不需要家长填写量表。
    通过记录频率变化、计划完成率和文本情绪信号间接建模。

    Args:
        record_count_7d: 本周记录条数
        record_count_prev_7d: 上周记录条数
        plan_completion_rate: 计划完成率（0.0-1.0）
        has_distress_language: 近期文本中是否出现困扰/焦虑语言
        has_positive_language: 近期文本中是否出现积极自评语言
        distress_weeks: 持续出现困扰语言的周数

    Returns:
        ParentWellbeing 实例
    """
    # 参与度趋势
    if record_count_prev_7d > 0:
        ratio = record_count_7d / record_count_prev_7d
        if ratio >= 1.2:
            engagement = "increasing"
        elif ratio <= 0.5:
            engagement = "decreasing"
        else:
            engagement = "stable"
    else:
        engagement = "stable" if record_count_7d > 0 else "decreasing"

    # 疲劳信号
    if record_count_7d == 0 and plan_completion_rate < 0.3:
        fatigue = "burnout_risk"
    elif record_count_7d <= 1 or plan_completion_rate < 0.4:
        fatigue = "fatigued"
    elif record_count_7d >= 4 and plan_completion_rate > 0.7:
        fatigue = "energized"
    else:
        fatigue = "normal"

    # 效能感信号
    if has_positive_language and plan_completion_rate > 0.5:
        efficacy = "confident"
    elif has_distress_language or plan_completion_rate < 0.3:
        efficacy = "struggling"
    else:
        efficacy = "neutral"

    # 支持偏好
    if fatigue == "burnout_risk" and distress_weeks >= 3:
        preference = "pause_and_rest"
    elif fatigue in ("fatigued", "burnout_risk"):
        preference = "light_plan"
    else:
        preference = "full_plan"

    return ParentWellbeing(
        efficacy_signal=efficacy,
        fatigue_signal=fatigue,
        engagement_trend=engagement,
        distress_weeks=distress_weeks,
        recent_positive_language=has_positive_language,
        support_preference=preference,
    )
