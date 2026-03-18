"""证据充分性检查 + 发展状态趋势引擎。

实现观测模型结构稿 V1.1 第九~十章的趋势判断规则：
- 主题聚合 + 时间窗口 + 升级条件
- 证据充分性四项检查：记录量、场景覆盖、照护者一致性、临时干扰
- 五级内部状态的自动判定与迁移

V2.0 专业化升级：
- 新增个体内比较（intra-individual comparison）：基线追踪 + 趋势方向
- 新增家长困扰度差异化处理：持续高困扰本身可触发关注提升（Glascoe 2000）
- 新增回应效果追踪字段：完善 Serve & Return 闭环
  V2.0b: 回应效果对状态判定产生实质影响：
  - ineffective + persistent_weak → CONSULT 升级（策略无效意味着当前方案需调整）
  - effective + improving → 趋势保护加固（有效策略应持续）
  - partial → 生成策略微调建议
- 趋势方向三态：improving / stable / declining

设计原则：
- 单次事件不升级
- 证据不足不强判
- 退步优先处理
- 缓慢进步不误判为持续偏弱（个体内比较优先）
- 回应效果参与判定但不单独触发升级
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Literal

from ai_parenting.models.enums import DevStatus, DevTheme, RiskLevel


# ---------------------------------------------------------------------------
# 趋势方向
# ---------------------------------------------------------------------------

TrendDirection = Literal["improving", "stable", "declining", "unknown"]
"""趋势方向：改善中 / 稳定 / 下滑中 / 未知（数据不足）。"""


# ---------------------------------------------------------------------------
# 证据充分性检查
# ---------------------------------------------------------------------------


@dataclass
class EvidenceInput:
    """单个主题的证据输入数据。

    由上层服务从数据库聚合后传入。

    V2.0 新增字段:
    - previous_status: 上周该主题的状态（用于个体内比较）
    - previous_weak_ratio: 上周偏弱比例（用于趋势方向判断）
    - distress_duration_weeks: 家长持续高困扰的周数
    - response_effectiveness: 照护者回应后的效果追踪
    """

    theme: DevTheme
    record_count_14d: int = 0            # 最近 14 天内有效记录数
    record_count_7d: int = 0             # 最近 7 天内有效记录数
    weekly_review_count: int = 0         # 最近 14 天内周回顾数
    scene_count: int = 0                 # 不同场景数
    caregiver_conflict: bool = False     # 照护者之间结论是否冲突
    has_temporary_disruption: bool = False  # 是否存在临时干扰（生病/旅行/搬家等）

    # 表现数据
    positive_count: int = 0              # 正面表现次数（出现/稳定）
    weak_count: int = 0                  # 偏弱表现次数（未见/需大量提示）
    regress_signal: bool = False         # 是否有退步信号（原有能力减少或消失）
    distress_level: Literal["low", "medium", "high"] = "low"  # 家长困扰度

    # V2.0: 基线追踪与个体内比较
    previous_status: DevStatus | None = None    # 上一评估周期的状态
    previous_weak_ratio: float | None = None    # 上一评估周期的偏弱比例
    distress_duration_weeks: int = 0            # 家长持续高困扰的连续周数

    # V2.0: 回应效果追踪（Serve & Return 闭环）
    response_effectiveness: Literal[
        "not_tracked", "effective", "partial", "ineffective"
    ] = "not_tracked"


@dataclass
class EvidenceSufficiency:
    """证据充分性检查结果。"""

    sufficient: bool = True
    flags: list[str] = field(default_factory=list)

    @property
    def summary(self) -> str:
        if self.sufficient:
            return "证据充分"
        return "；".join(self.flags)


def check_evidence_sufficiency(evidence: EvidenceInput) -> EvidenceSufficiency:
    """执行证据充分性四项检查。

    来源：观测模型 V1.1 第十章。

    规则：
    1. 最小记录量：14 天内 ≥ 3 条，或"2 条日常记录 + 1 次周回顾"
    2. 场景覆盖：至少 2 个场景
    3. 照护者一致性：结论不应明显冲突
    4. 观察频率：7 天内至少 2 次记录
    5. 临时干扰：标记后降权
    """
    result = EvidenceSufficiency()

    # 规则 1：最小记录量
    has_min_records = evidence.record_count_14d >= 3
    has_alt_records = evidence.record_count_14d >= 2 and evidence.weekly_review_count >= 1
    if not has_min_records and not has_alt_records:
        result.sufficient = False
        result.flags.append("记录量不足：最近 14 天内需至少 3 条记录或 2 条记录 + 1 次周回顾")

    # 规则 2：场景覆盖
    if evidence.scene_count < 2 and evidence.record_count_14d >= 2:
        # 单场景下多次出现不自动视为趋势，但不一定完全不充分
        result.flags.append("场景偏窄：仅覆盖单一场景，单场景异常不直接视为趋势")

    # 规则 3：照护者一致性
    if evidence.caregiver_conflict:
        result.sufficient = False
        result.flags.append("照护者口径冲突：需追加补充记录校准")

    # 规则 4：观察频率
    if evidence.record_count_7d < 2 and evidence.record_count_14d >= 3:
        result.flags.append("近期频率偏低：最近 7 天内记录不足 2 次")

    # 规则 5：临时干扰
    if evidence.has_temporary_disruption:
        result.flags.append("存在临时干扰因素（生病/旅行/搬家等），该时段记录降权")

    return result


# ---------------------------------------------------------------------------
# 趋势判断引擎
# ---------------------------------------------------------------------------


@dataclass
class TrendResult:
    """趋势判断结果。

    V2.0 新增:
    - trend_direction: 趋势方向（improving/stable/declining/unknown）
    - parent_distress_note: 家长困扰度相关的补充说明
    - response_note: 回应效果追踪补充说明
    """

    theme: DevTheme
    status: DevStatus
    risk_level: RiskLevel
    evidence_check: EvidenceSufficiency
    reasoning: str = ""
    action_hint: Literal["keep_observing", "weekly_focus", "supplement_or_consult"] = "keep_observing"
    trend_direction: TrendDirection = "unknown"
    parent_distress_note: str = ""
    response_note: str = ""

    @property
    def action_display(self) -> str:
        _map = {
            "keep_observing": "继续给机会",
            "weekly_focus": "本周重点练习",
            "supplement_or_consult": "补充观察或咨询",
        }
        return _map.get(self.action_hint, self.action_hint)

    @property
    def trend_display(self) -> str:
        """趋势方向的中文显示。"""
        _map = {
            "improving": "趋势向好",
            "stable": "保持稳定",
            "declining": "有所下滑",
            "unknown": "数据不足",
        }
        return _map.get(self.trend_direction, self.trend_direction)


def _compute_trend_direction(evidence: EvidenceInput, current_weak_ratio: float) -> TrendDirection:
    """基于个体内比较计算趋势方向。

    核心逻辑：拿孩子跟自己的上周比，不跟"标准"比。
    - 偏弱比例下降 ≥ 10%: improving
    - 偏弱比例上升 ≥ 10%: declining
    - 其他: stable
    - 无前期数据: unknown
    """
    if evidence.previous_weak_ratio is None:
        return "unknown"

    delta = current_weak_ratio - evidence.previous_weak_ratio

    if delta <= -0.10:  # 偏弱比例下降 10% 以上 → 在改善
        return "improving"
    elif delta >= 0.10:  # 偏弱比例上升 10% 以上 → 在下滑
        return "declining"
    else:
        return "stable"


def assess_theme_status(evidence: EvidenceInput) -> TrendResult:
    """评估单个主题的发展状态。

    来源：观测模型 V1.1 第八~十章趋势判断逻辑。

    V2.0 升级：
    - 增加个体内比较：通过 previous_status 和 previous_weak_ratio 判断趋势方向
    - 增加"缓慢进步"保护：即使当前偏弱比例仍高，如果趋势在改善则不升级风险
    - 增加家长困扰度差异化：持续高困扰 ≥ 2 周本身触发关注提升（Glascoe 2000）
    - 增加回应效果追踪：回应无效时补充说明

    核心规则：
    - 退步信号优先处理，可跳过部分频率门槛
    - 证据不足时不升级为"持续偏弱"，保留"待补充观察"
    - 单次事件不升级
    - 趋势在改善时，不因当前快照偏弱而过度升级
    """
    ev_check = check_evidence_sufficiency(evidence)

    # 退步信号优先处理——不需要等待完整两周
    if evidence.regress_signal:
        return TrendResult(
            theme=evidence.theme,
            status=DevStatus.REGRESSING,
            risk_level=RiskLevel.CONSULT,
            evidence_check=ev_check,
            reasoning="检测到退步信号：原有能力明显减少或消失，优先进入更高提醒层",
            action_hint="supplement_or_consult",
            trend_direction="declining",
        )

    # 证据不充分——不做强判断
    if not ev_check.sufficient:
        return TrendResult(
            theme=evidence.theme,
            status=DevStatus.INSUFFICIENT,
            risk_level=RiskLevel.NORMAL,
            evidence_check=ev_check,
            reasoning=f"证据不足以做趋势判断：{ev_check.summary}",
            action_hint="keep_observing",
            trend_direction="unknown",
        )

    # 临时干扰期间降权
    if evidence.has_temporary_disruption:
        return TrendResult(
            theme=evidence.theme,
            status=DevStatus.FLUCTUATING,
            risk_level=RiskLevel.NORMAL,
            evidence_check=ev_check,
            reasoning="存在临时干扰因素，该时段表现降权处理，不作为升级依据",
            action_hint="keep_observing",
            trend_direction="unknown",
        )

    total_records = evidence.positive_count + evidence.weak_count
    if total_records == 0:
        return TrendResult(
            theme=evidence.theme,
            status=DevStatus.INSUFFICIENT,
            risk_level=RiskLevel.NORMAL,
            evidence_check=ev_check,
            reasoning="无有效表现记录",
            action_hint="keep_observing",
            trend_direction="unknown",
        )

    weak_ratio = evidence.weak_count / total_records
    trend_dir = _compute_trend_direction(evidence, weak_ratio)

    # --- 家长困扰度差异化处理 (Glascoe 2000) ---
    # 持续高困扰 ≥ 2 周，即使孩子表现在正常范围，也提升关注
    parent_distress_note = ""
    distress_risk_boost = False
    if evidence.distress_level == "high" and evidence.distress_duration_weeks >= 2:
        parent_distress_note = (
            f"家长已持续 {evidence.distress_duration_weeks} 周表达高度困扰，"
            "建议关注家长情绪状态并考虑是否需要额外支持"
        )
        distress_risk_boost = True

    # --- 回应效果追踪（V2.0b 增强：对状态判定产生实质影响） ---
    response_note = ""
    response_ineffective = False
    response_effective = False
    if evidence.response_effectiveness == "ineffective":
        response_note = "近期记录显示照护者当前回应策略效果不佳，建议在计划中调整互动方式"
        response_ineffective = True
    elif evidence.response_effectiveness == "effective":
        response_note = "当前回应策略有效，建议在计划中继续强化此方式"
        response_effective = True
    elif evidence.response_effectiveness == "partial":
        response_note = "当前回应策略部分有效，建议微调互动方式——保留有效部分，调整效果不明显的环节"

    # --- 持续偏弱判定（增加个体内比较保护 + 回应效果影响） ---
    if weak_ratio > 0.6 and evidence.scene_count >= 2:
        # V2.0 关键升级：如果趋势在改善，降低风险等级
        if trend_dir == "improving":
            # V2.0b: effective + improving → 趋势保护加固
            effective_note = ""
            if response_effective:
                effective_note = "，且当前回应策略有效，建议继续"
            return TrendResult(
                theme=evidence.theme,
                status=DevStatus.FLUCTUATING,
                risk_level=RiskLevel.ATTENTION if distress_risk_boost else RiskLevel.NORMAL,
                evidence_check=ev_check,
                reasoning=(
                    f"偏弱比例 {weak_ratio:.0%}，但趋势在改善"
                    f"（上周 {evidence.previous_weak_ratio:.0%} → 本周 {weak_ratio:.0%}）"
                    f"{effective_note}，"
                    "属于缓慢进步，保持关注而非升级"
                ),
                action_hint="weekly_focus",
                trend_direction=trend_dir,
                parent_distress_note=parent_distress_note,
                response_note=response_note,
            )

        # 不在改善的持续偏弱
        risk = RiskLevel.ATTENTION
        # V2.0b: ineffective + persistent_weak → 触发 CONSULT 升级
        # 策略无效意味着当前方案需要专业支持来调整
        if distress_risk_boost or response_ineffective:
            risk = RiskLevel.CONSULT

        ineffective_reasoning = ""
        if response_ineffective:
            ineffective_reasoning = "，回应策略效果不佳需调整"

        return TrendResult(
            theme=evidence.theme,
            status=DevStatus.PERSISTENT_WEAK,
            risk_level=risk,
            evidence_check=ev_check,
            reasoning=(
                f"偏弱比例 {weak_ratio:.0%}，跨 {evidence.scene_count} 个场景"
                + (f"，趋势 {trend_dir}" if trend_dir != "unknown" else "")
                + (f"，家长困扰度高" if evidence.distress_level == "high" else "")
                + ineffective_reasoning
            ),
            action_hint="supplement_or_consult" if risk == RiskLevel.CONSULT else "weekly_focus",
            trend_direction=trend_dir,
            parent_distress_note=parent_distress_note,
            response_note=response_note,
        )

    # --- 偶有波动 ---
    if weak_ratio > 0.3 or (evidence.weak_count > 0 and evidence.scene_count < 2):
        risk = RiskLevel.ATTENTION if distress_risk_boost else RiskLevel.NORMAL
        return TrendResult(
            theme=evidence.theme,
            status=DevStatus.FLUCTUATING,
            risk_level=risk,
            evidence_check=ev_check,
            reasoning=f"偏弱比例 {weak_ratio:.0%}，属于阶段内常见波动",
            action_hint="weekly_focus" if distress_risk_boost else "keep_observing",
            trend_direction=trend_dir,
            parent_distress_note=parent_distress_note,
            response_note=response_note,
        )

    # --- 稳定出现 ---
    risk = RiskLevel.NORMAL
    if distress_risk_boost:
        risk = RiskLevel.ATTENTION
        parent_distress_note += "；虽然孩子表现稳定，但家长困扰度持续较高，建议关注家长需求"

    return TrendResult(
        theme=evidence.theme,
        status=DevStatus.STABLE,
        risk_level=risk,
        evidence_check=ev_check,
        reasoning=f"正面表现比例 {1 - weak_ratio:.0%}，多场景稳定出现",
        action_hint="keep_observing",
        trend_direction=trend_dir,
        parent_distress_note=parent_distress_note,
        response_note=response_note,
    )


def assess_all_themes(evidences: list[EvidenceInput]) -> list[TrendResult]:
    """批量评估所有主题的发展状态。"""
    results = [assess_theme_status(ev) for ev in evidences]

    # 多主题并存检查：如果有 2 个以上主题同时为 persistent_weak 或 regressing，
    # 整体风险应提升
    high_risk_count = sum(
        1 for r in results
        if r.status in (DevStatus.PERSISTENT_WEAK, DevStatus.REGRESSING)
    )

    if high_risk_count >= 2:
        for r in results:
            if r.status == DevStatus.PERSISTENT_WEAK:
                r.risk_level = RiskLevel.CONSULT
                r.reasoning += "；多主题同时偏弱，建议咨询"
                r.action_hint = "supplement_or_consult"

    return results
