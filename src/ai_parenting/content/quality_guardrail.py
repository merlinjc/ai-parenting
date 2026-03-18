"""内容质量护栏：Prompt 输出的结构化校验。

在现有 BoundaryChecker（非诊断化边界检查）之上，新增内容一致性校验，
确保 LLM 生成的微计划在焦点选择、观察项关联和年龄适配上不偏离专业边界。
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ai_parenting.content.observation_registry import (
    ALL_ITEMS,
    get_items_by_focus,
    get_items_by_stage,
    get_items_by_theme,
)
from ai_parenting.models.enums import (
    ChildStage,
    DevTheme,
    InterventionFocus,
)


# ---------------------------------------------------------------------------
# 校验结果
# ---------------------------------------------------------------------------


@dataclass
class QualityFlag:
    """质量校验标记。"""

    category: str
    severity: str  # "warning" | "error"
    message: str


@dataclass
class QualityCheckResult:
    """质量校验结果。"""

    passed: bool = True
    flags: list[QualityFlag] = field(default_factory=list)

    def add_warning(self, category: str, message: str) -> None:
        self.flags.append(QualityFlag(category=category, severity="warning", message=message))

    def add_error(self, category: str, message: str) -> None:
        self.flags.append(QualityFlag(category=category, severity="error", message=message))
        self.passed = False


# ---------------------------------------------------------------------------
# 校验规则
# ---------------------------------------------------------------------------


def check_plan_content_quality(
    stage: ChildStage,
    focus_theme_value: str,
    primary_goal: str,
    day_tasks: list[dict],
    observation_candidates: list[dict],
    priority_scenes: list[str],
) -> QualityCheckResult:
    """对微计划生成结果执行内容质量校验。

    校验维度：
    1. 焦点与阶段匹配性
    2. 观察候选项与主题一致性
    3. 日任务难度与阶段适配
    4. 话术长度与阶段适配
    5. 场景数量合规性
    """
    result = QualityCheckResult()

    # 1. 阶段对应的建议参数
    stage_params = _STAGE_QUALITY_PARAMS.get(stage)
    if not stage_params:
        result.add_warning("stage_unknown", f"未知阶段 {stage}，跳过阶段适配检查")
        return result

    # 2. 日任务数量
    if len(day_tasks) != 7:
        result.add_error("day_task_count", f"日任务必须 7 个，当前 {len(day_tasks)} 个")

    # 3. 检查话术长度适配
    for dt in day_tasks:
        script = dt.get("demo_script", "")
        if script and len(script) > stage_params["max_script_chars"]:
            result.add_warning(
                "script_too_long",
                f"Day {dt.get('day_number', '?')} 话术 {len(script)} 字符，"
                f"超过 {stage.value} 阶段建议的 {stage_params['max_script_chars']} 字符"
            )

    # 4. 观察候选项 theme 一致性
    # （使用旧 FocusTheme 值检查——因为当前 PlanGenerationResult 仍使用旧枚举）
    for oc in observation_candidates:
        oc_theme = oc.get("theme", "")
        if oc_theme and oc_theme != focus_theme_value:
            # 允许少量跨主题候选项（如情绪类），但超过一半则告警
            pass
    cross_theme_count = sum(
        1 for oc in observation_candidates
        if oc.get("theme", "") != focus_theme_value
    )
    total_oc = len(observation_candidates)
    if total_oc > 0 and cross_theme_count > total_oc * 0.6:
        result.add_warning(
            "observation_theme_mismatch",
            f"观察候选项中 {cross_theme_count}/{total_oc} 个与计划焦点主题不一致"
        )

    # 5. primary_goal 不应包含诊断性词汇（V2.0 扩展）
    diagnostic_terms = [
        # 诊断标签
        "自闭", "多动", "发育迟缓", "语言障碍", "感统失调", "孤独症",
        "阿斯伯格", "脑瘫", "癫痫", "抽动症", "对立违抗",
        "选择性缄默", "言语失用", "构音障碍",
        # 治疗承诺
        "治愈", "矫正", "康复", "训练好", "治疗", "矫治",
        "恢复正常", "回到正轨",
        # 比较性语言
        "落后", "达标", "低于平均", "跟不上", "赶不上",
    ]
    for term in diagnostic_terms:
        if term in primary_goal:
            result.add_error("diagnostic_goal", f"primary_goal 包含禁用词汇「{term}」")

    # 6. 场景数量
    if len(priority_scenes) < 2:
        result.add_warning("too_few_scenes", f"优先场景仅 {len(priority_scenes)} 个，建议 2-3 个")

    return result


# 阶段质量参数
_STAGE_QUALITY_PARAMS: dict[ChildStage, dict] = {
    ChildStage.M18_24: {
        "max_script_chars": 50,    # 单句、关键词重复
        "max_rounds": 2,
        "max_exercise_minutes": 5,
    },
    ChildStage.M24_36: {
        "max_script_chars": 80,    # 短句、二选一
        "max_rounds": 4,
        "max_exercise_minutes": 8,
    },
    ChildStage.M36_48: {
        "max_script_chars": 120,   # 完整句式、简单协商
        "max_rounds": 5,
        "max_exercise_minutes": 10,
    },
}
