"""睡眠分析技能 — Phase 3 原生 Skill 示范。

展示如何从零开发一个新技能（无需 Adapter 桥接）。
新技能只需：
1. 继承 Skill 基类
2. 实现 metadata / execute / get_boundary_rules
3. 放到 skills/adapters/ 目录下（自动发现注册）
4. 可选：实现 Orchestrator 模式方法（render_prompt/parse_result/...）

功能：
- 接收 7 天睡眠记录
- 分析睡眠模式（入睡时间规律性、总时长趋势、夜醒频率）
- 返回评估等级 + 个性化建议
"""

from __future__ import annotations

import logging
import statistics
from typing import Any

from pydantic import BaseModel, Field

from ai_parenting.skills.base import BoundaryRule, Skill, SkillMetadata, SkillResult

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# 睡眠分析输入/输出 Schema
# ---------------------------------------------------------------------------


class SleepRecord(BaseModel):
    """单日睡眠记录。"""

    date: str  # YYYY-MM-DD
    bedtime: str  # HH:MM（入睡时间）
    wake_time: str  # HH:MM（醒来时间）
    total_hours: float  # 总睡眠时长（小时）
    night_wakings: int = 0  # 夜醒次数
    nap_hours: float = 0.0  # 白天小睡时长（小时）


class SleepAnalysisInput(BaseModel):
    """睡眠分析输入。"""

    child_age_months: int
    sleep_records: list[SleepRecord] = Field(min_length=1, max_length=14)


class SleepAnalysisResult(BaseModel):
    """睡眠分析结果。"""

    overall_rating: str  # "excellent" | "good" | "needs_improvement" | "concerning"
    rating_display: str  # "很棒" | "良好" | "待改善" | "需关注"
    avg_total_hours: float
    avg_night_wakings: float
    bedtime_consistency: str  # "高" | "中" | "低"
    summary_text: str  # 一句话总结
    recommendations: list[str]  # 建议列表
    age_reference: str  # 该月龄建议睡眠时长参考


# ---------------------------------------------------------------------------
# 月龄对应睡眠参考
# ---------------------------------------------------------------------------

_AGE_SLEEP_REFERENCE: dict[tuple[int, int], dict[str, Any]] = {
    (18, 24): {"total": (12, 14), "night": (10, 12), "nap": (1.5, 3), "label": "18-24个月"},
    (24, 36): {"total": (11, 14), "night": (10, 12), "nap": (1, 3), "label": "2-3岁"},
    (36, 48): {"total": (10, 13), "night": (10, 12), "nap": (0, 2), "label": "3-4岁"},
}


def _get_age_reference(age_months: int) -> dict[str, Any]:
    for (low, high), ref in _AGE_SLEEP_REFERENCE.items():
        if low <= age_months < high:
            return ref
    # 默认使用 24-36 月
    return _AGE_SLEEP_REFERENCE[(24, 36)]


# ---------------------------------------------------------------------------
# 睡眠分析技能
# ---------------------------------------------------------------------------


class SleepAnalysisSkill(Skill):
    """睡眠分析原生技能。

    不需要 AI 模型调用——基于规则分析睡眠数据。
    未来可升级为 supports_orchestrate=True 的 AI 增强版本。
    """

    @property
    def metadata(self) -> SkillMetadata:
        return SkillMetadata(
            name="sleep_analysis",
            display_name="睡眠分析",
            description="分析近期睡眠数据，评估睡眠质量并提供个性化改善建议",
            version="1.0.0",
            icon="🌙",
            tags=["sleep", "睡眠", "夜醒", "入睡", "sleep_analysis"],
            input_schema=SleepAnalysisInput,
            output_schema=SleepAnalysisResult,
            is_enabled=True,
            session_type="sleep_analysis",
        )

    async def execute(self, params: dict[str, Any], context: Any) -> SkillResult:
        """执行睡眠分析。

        params 中期望的字段：
        - child_age_months: int — 孩子月龄
        - sleep_records: list[dict] — 睡眠记录列表
        - 或 user_input_text: str — 语音输入文本（简化模式）
        """
        try:
            age_months = params.get("child_age_months")
            records_raw = params.get("sleep_records", [])

            if not records_raw:
                return SkillResult(
                    response_text="暂时没有睡眠记录数据，请先在 App 中添加最近 7 天的睡眠记录后再试。",
                    boundary_passed=True,
                    is_degraded=True,
                    metadata={"reason": "no_records"},
                )

            if age_months is None:
                # 从 context 获取
                if context and hasattr(context, "child_age_months"):
                    age_months = context.child_age_months
                else:
                    age_months = 24  # 默认

            # 解析记录
            records: list[SleepRecord] = []
            for r in records_raw:
                if isinstance(r, dict):
                    records.append(SleepRecord(**r))
                elif isinstance(r, SleepRecord):
                    records.append(r)

            if not records:
                return SkillResult(
                    response_text="睡眠记录格式有问题，请检查后重试。",
                    boundary_passed=True,
                    is_degraded=True,
                )

            # 执行分析
            result = self._analyze(age_months, records)

            return SkillResult(
                response_text=result.summary_text,
                structured_data=result,
                boundary_passed=True,
                metadata={
                    "record_count": len(records),
                    "rating": result.overall_rating,
                },
            )

        except Exception as exc:
            logger.error("SleepAnalysisSkill execute failed: %s", exc)
            return SkillResult(
                response_text="睡眠分析遇到了问题，请稍后重试。",
                boundary_passed=True,
                is_degraded=True,
                metadata={"error": str(exc)},
            )

    def _analyze(self, age_months: int, records: list[SleepRecord]) -> SleepAnalysisResult:
        """基于规则的睡眠分析。"""
        ref = _get_age_reference(age_months)
        total_hours_list = [r.total_hours for r in records]
        night_wakings_list = [r.night_wakings for r in records]

        avg_total = statistics.mean(total_hours_list)
        avg_wakings = statistics.mean(night_wakings_list)

        # 入睡时间规律性（标准差）
        bedtime_minutes: list[float] = []
        for r in records:
            try:
                h, m = map(int, r.bedtime.split(":"))
                # 晚上的时间转换（22:00 → 1320, 次日 00:30 → 1470）
                total_min = h * 60 + m
                if total_min < 360:  # 凌晨 6 点前算前一天晚上
                    total_min += 1440
                bedtime_minutes.append(total_min)
            except (ValueError, AttributeError):
                pass

        if len(bedtime_minutes) >= 2:
            bedtime_std = statistics.stdev(bedtime_minutes)
            if bedtime_std < 30:
                bedtime_consistency = "高"
            elif bedtime_std < 60:
                bedtime_consistency = "中"
            else:
                bedtime_consistency = "低"
        else:
            bedtime_consistency = "中"

        # 评级
        ref_total_low, ref_total_high = ref["total"]
        recommendations: list[str] = []

        if avg_total >= ref_total_low and avg_wakings <= 1 and bedtime_consistency in ("高", "中"):
            overall_rating = "excellent"
            rating_display = "很棒"
            summary_parts = [f"宝宝近期睡眠质量很棒！平均每天睡 {avg_total:.1f} 小时，"]
        elif avg_total >= ref_total_low and avg_wakings <= 2:
            overall_rating = "good"
            rating_display = "良好"
            summary_parts = [f"宝宝睡眠质量良好，平均每天 {avg_total:.1f} 小时，"]
        elif avg_total >= ref_total_low - 1:
            overall_rating = "needs_improvement"
            rating_display = "待改善"
            summary_parts = [f"宝宝睡眠有改善空间，平均 {avg_total:.1f} 小时，"]
        else:
            overall_rating = "concerning"
            rating_display = "需关注"
            summary_parts = [f"宝宝近期睡眠不太理想，平均只有 {avg_total:.1f} 小时，"]

        # 夜醒分析
        if avg_wakings > 2:
            summary_parts.append(f"夜醒较频繁（平均 {avg_wakings:.1f} 次）。")
            recommendations.append("减少睡前刺激活动，建立固定的睡前仪式（洗澡→绘本→哄睡）")
            recommendations.append("夜醒时先观察等待 1-2 分钟再介入，培养自主入睡能力")
        elif avg_wakings > 1:
            summary_parts.append(f"偶有夜醒（平均 {avg_wakings:.1f} 次）。")
            recommendations.append("保持睡眠环境安静，控制夜间室温在 20-22°C")
        else:
            summary_parts.append("夜醒很少，自主睡眠能力不错。")

        # 入睡规律性
        if bedtime_consistency == "低":
            recommendations.append("每天固定入睡时间（误差不超过 30 分钟），建立生物钟")
        elif bedtime_consistency == "中":
            recommendations.append("入睡时间基本规律，继续保持，建议误差控制在 15 分钟以内")

        # 总时长建议
        if avg_total < ref_total_low:
            gap = ref_total_low - avg_total
            recommendations.append(
                f"建议增加约 {gap:.1f} 小时睡眠，{ref['label']}宝宝推荐 {ref_total_low}-{ref_total_high} 小时/天"
            )

        # 兜底建议
        if not recommendations:
            recommendations.append("继续保持良好的睡眠习惯！")
            recommendations.append("可以尝试记录白天小睡时间，观察是否影响夜间入睡")

        age_ref_text = (
            f"{ref['label']}宝宝建议总睡眠 {ref_total_low}-{ref_total_high} 小时/天，"
            f"其中夜间 {ref['night'][0]}-{ref['night'][1]} 小时"
        )

        return SleepAnalysisResult(
            overall_rating=overall_rating,
            rating_display=rating_display,
            avg_total_hours=round(avg_total, 1),
            avg_night_wakings=round(avg_wakings, 1),
            bedtime_consistency=bedtime_consistency,
            summary_text="".join(summary_parts),
            recommendations=recommendations,
            age_reference=age_ref_text,
        )

    def get_boundary_rules(self) -> list[BoundaryRule]:
        return [
            BoundaryRule(
                category="diagnosis_label",
                description="禁止在睡眠分析中出现医学诊断标签（如'睡眠障碍'等）",
            ),
            BoundaryRule(
                category="overquantify",
                description="禁止将睡眠分析结果与具体医学百分位数关联",
            ),
        ]
