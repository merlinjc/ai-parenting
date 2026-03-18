"""测试：证据充分性检查 + 发展状态趋势引擎。"""

from ai_parenting.content.evidence_engine import (
    EvidenceInput,
    EvidenceSufficiency,
    TrendResult,
    assess_all_themes,
    assess_theme_status,
    check_evidence_sufficiency,
)
from ai_parenting.models.enums import DevStatus, DevTheme, RiskLevel


class TestEvidenceSufficiency:
    """证据充分性检查。"""

    def test_sufficient_evidence(self):
        ev = EvidenceInput(
            theme=DevTheme.EXPRESSION_NEED,
            record_count_14d=5,
            record_count_7d=3,
            scene_count=2,
        )
        result = check_evidence_sufficiency(ev)
        assert result.sufficient is True

    def test_insufficient_records(self):
        ev = EvidenceInput(
            theme=DevTheme.EXPRESSION_NEED,
            record_count_14d=1,
            record_count_7d=1,
        )
        result = check_evidence_sufficiency(ev)
        assert result.sufficient is False
        assert any("记录量不足" in f for f in result.flags)

    def test_alt_records_with_review(self):
        """2 条记录 + 1 次周回顾也够。"""
        ev = EvidenceInput(
            theme=DevTheme.EXPRESSION_NEED,
            record_count_14d=2,
            record_count_7d=2,
            weekly_review_count=1,
            scene_count=2,
        )
        result = check_evidence_sufficiency(ev)
        assert result.sufficient is True

    def test_single_scene_warning(self):
        ev = EvidenceInput(
            theme=DevTheme.JOINT_ATTENTION,
            record_count_14d=4,
            record_count_7d=3,
            scene_count=1,
        )
        result = check_evidence_sufficiency(ev)
        assert any("场景偏窄" in f for f in result.flags)

    def test_caregiver_conflict(self):
        ev = EvidenceInput(
            theme=DevTheme.IMITATION_TURN,
            record_count_14d=5,
            record_count_7d=3,
            scene_count=2,
            caregiver_conflict=True,
        )
        result = check_evidence_sufficiency(ev)
        assert result.sufficient is False
        assert any("照护者" in f for f in result.flags)

    def test_temporary_disruption_flag(self):
        ev = EvidenceInput(
            theme=DevTheme.EMOTION_TRANSITION,
            record_count_14d=4,
            record_count_7d=2,
            scene_count=2,
            has_temporary_disruption=True,
        )
        result = check_evidence_sufficiency(ev)
        assert any("临时干扰" in f for f in result.flags)

    def test_low_frequency_warning(self):
        ev = EvidenceInput(
            theme=DevTheme.SOCIAL_APPROACH,
            record_count_14d=4,
            record_count_7d=1,
            scene_count=2,
        )
        result = check_evidence_sufficiency(ev)
        assert any("频率偏低" in f for f in result.flags)


class TestTrendJudgment:
    """趋势判断引擎。"""

    def test_regress_priority(self):
        """退步信号优先，即使记录不足。"""
        ev = EvidenceInput(
            theme=DevTheme.EXPRESSION_NEED,
            record_count_14d=2,
            record_count_7d=1,
            regress_signal=True,
        )
        result = assess_theme_status(ev)
        assert result.status == DevStatus.REGRESSING
        assert result.risk_level == RiskLevel.CONSULT
        assert result.action_hint == "supplement_or_consult"

    def test_insufficient_evidence(self):
        ev = EvidenceInput(
            theme=DevTheme.JOINT_ATTENTION,
            record_count_14d=1,
        )
        result = assess_theme_status(ev)
        assert result.status == DevStatus.INSUFFICIENT
        assert result.risk_level == RiskLevel.NORMAL

    def test_temporary_disruption_downweight(self):
        ev = EvidenceInput(
            theme=DevTheme.EMOTION_TRANSITION,
            record_count_14d=5,
            record_count_7d=3,
            scene_count=2,
            has_temporary_disruption=True,
            positive_count=1,
            weak_count=4,
        )
        result = assess_theme_status(ev)
        assert result.status == DevStatus.FLUCTUATING
        assert result.risk_level == RiskLevel.NORMAL

    def test_stable_status(self):
        ev = EvidenceInput(
            theme=DevTheme.EXPRESSION_NEED,
            record_count_14d=6,
            record_count_7d=3,
            scene_count=3,
            positive_count=5,
            weak_count=1,
        )
        result = assess_theme_status(ev)
        assert result.status == DevStatus.STABLE
        assert result.risk_level == RiskLevel.NORMAL
        assert result.action_hint == "keep_observing"

    def test_fluctuating_status(self):
        ev = EvidenceInput(
            theme=DevTheme.IMITATION_TURN,
            record_count_14d=5,
            record_count_7d=3,
            scene_count=2,
            positive_count=3,
            weak_count=2,
        )
        result = assess_theme_status(ev)
        assert result.status == DevStatus.FLUCTUATING

    def test_persistent_weak_status(self):
        ev = EvidenceInput(
            theme=DevTheme.SOCIAL_APPROACH,
            record_count_14d=5,
            record_count_7d=3,
            scene_count=2,
            positive_count=1,
            weak_count=4,
            distress_level="high",
        )
        result = assess_theme_status(ev)
        assert result.status == DevStatus.PERSISTENT_WEAK
        assert result.risk_level == RiskLevel.ATTENTION
        assert result.action_hint == "weekly_focus"

    def test_single_scene_weak_stays_fluctuating(self):
        """单场景偏弱不直接升级。"""
        ev = EvidenceInput(
            theme=DevTheme.PLAY_NARRATIVE,
            record_count_14d=5,
            record_count_7d=3,
            scene_count=1,
            positive_count=2,
            weak_count=3,
        )
        result = assess_theme_status(ev)
        assert result.status == DevStatus.FLUCTUATING


class TestMultiThemeEscalation:
    """多主题并存升级。"""

    def test_two_persistent_weak_escalates(self):
        evidences = [
            EvidenceInput(
                theme=DevTheme.EXPRESSION_NEED,
                record_count_14d=5, record_count_7d=3, scene_count=2,
                positive_count=1, weak_count=4,
            ),
            EvidenceInput(
                theme=DevTheme.IMITATION_TURN,
                record_count_14d=5, record_count_7d=3, scene_count=2,
                positive_count=1, weak_count=4,
            ),
            EvidenceInput(
                theme=DevTheme.JOINT_ATTENTION,
                record_count_14d=5, record_count_7d=3, scene_count=2,
                positive_count=4, weak_count=1,
            ),
        ]
        results = assess_all_themes(evidences)
        # 有 2 个 persistent_weak，应升级为 consult
        weak_results = [r for r in results if r.status == DevStatus.PERSISTENT_WEAK]
        assert len(weak_results) == 2
        for r in weak_results:
            assert r.risk_level == RiskLevel.CONSULT
            assert "多主题" in r.reasoning


# ---------------------------------------------------------------------------
# V2.0 新增：回应效果追踪测试
# ---------------------------------------------------------------------------


class TestResponseEffectiveness:
    """V2.0 回应效果追踪对状态判定的实质影响。"""

    def test_ineffective_with_persistent_weak_escalates_to_consult(self):
        """回应无效 + 持续偏弱 → CONSULT 升级。"""
        ev = EvidenceInput(
            theme=DevTheme.SENSORY_PROCESSING,
            record_count_14d=5, record_count_7d=3, scene_count=2,
            positive_count=1, weak_count=4,
            response_effectiveness="ineffective",
        )
        result = assess_theme_status(ev)
        assert result.status == DevStatus.PERSISTENT_WEAK
        assert result.risk_level == RiskLevel.CONSULT
        assert "回应策略" in result.response_note
        assert "效果不佳" in result.response_note

    def test_ineffective_alone_does_not_escalate_stable(self):
        """回应无效但表现稳定 → 不升级，仅生成提示。"""
        ev = EvidenceInput(
            theme=DevTheme.ATTACHMENT_SECURITY,
            record_count_14d=6, record_count_7d=3, scene_count=3,
            positive_count=5, weak_count=1,
            response_effectiveness="ineffective",
        )
        result = assess_theme_status(ev)
        assert result.status == DevStatus.STABLE
        assert result.risk_level == RiskLevel.NORMAL
        assert "调整互动方式" in result.response_note

    def test_effective_with_improving_trend_protection(self):
        """回应有效 + 趋势改善 → 缓慢进步保护加固。"""
        ev = EvidenceInput(
            theme=DevTheme.EXPRESSION_NEED,
            record_count_14d=6, record_count_7d=3, scene_count=2,
            positive_count=2, weak_count=4,
            previous_weak_ratio=0.85,  # 上周 85% 偏弱 → 本周 67%（降幅 18%）
            response_effectiveness="effective",
        )
        result = assess_theme_status(ev)
        # 当前 67% 偏弱，但从 85% 下降，趋势在改善
        assert result.status == DevStatus.FLUCTUATING  # 保护降级
        assert result.trend_direction == "improving"
        assert "有效" in result.response_note

    def test_partial_generates_adjustment_note(self):
        """回应部分有效 → 生成微调建议。"""
        ev = EvidenceInput(
            theme=DevTheme.IMITATION_TURN,
            record_count_14d=5, record_count_7d=3, scene_count=2,
            positive_count=3, weak_count=2,
            response_effectiveness="partial",
        )
        result = assess_theme_status(ev)
        assert "微调" in result.response_note

    def test_not_tracked_no_note(self):
        """未追踪 → 不生成 response_note。"""
        ev = EvidenceInput(
            theme=DevTheme.JOINT_ATTENTION,
            record_count_14d=5, record_count_7d=3, scene_count=2,
            positive_count=4, weak_count=1,
            response_effectiveness="not_tracked",
        )
        result = assess_theme_status(ev)
        assert result.response_note == ""


# ---------------------------------------------------------------------------
# V2.0 新增：个体内比较（趋势方向）测试
# ---------------------------------------------------------------------------


class TestTrendDirection:
    """V2.0 个体内比较——趋势方向判定。"""

    def test_improving_trend(self):
        """偏弱比例下降 ≥ 10% → improving。"""
        ev = EvidenceInput(
            theme=DevTheme.EXPRESSION_NEED,
            record_count_14d=5, record_count_7d=3, scene_count=2,
            positive_count=2, weak_count=3,
            previous_weak_ratio=0.8,  # 上周 80% → 本周 60%
        )
        result = assess_theme_status(ev)
        assert result.trend_direction == "improving"

    def test_declining_trend(self):
        """偏弱比例上升 ≥ 10% → declining。"""
        ev = EvidenceInput(
            theme=DevTheme.SOCIAL_APPROACH,
            record_count_14d=5, record_count_7d=3, scene_count=2,
            positive_count=2, weak_count=3,
            previous_weak_ratio=0.4,  # 上周 40% → 本周 60%
        )
        result = assess_theme_status(ev)
        assert result.trend_direction == "declining"

    def test_stable_trend(self):
        """偏弱比例变化 < 10% → stable。"""
        ev = EvidenceInput(
            theme=DevTheme.PLAY_NARRATIVE,
            record_count_14d=5, record_count_7d=3, scene_count=2,
            positive_count=3, weak_count=2,
            previous_weak_ratio=0.38,  # 上周 38% → 本周 40%
        )
        result = assess_theme_status(ev)
        assert result.trend_direction == "stable"

    def test_unknown_trend_without_previous(self):
        """无前期数据 → unknown。"""
        ev = EvidenceInput(
            theme=DevTheme.EMOTION_TRANSITION,
            record_count_14d=5, record_count_7d=3, scene_count=2,
            positive_count=4, weak_count=1,
        )
        result = assess_theme_status(ev)
        assert result.trend_direction == "unknown"

    def test_improving_protects_from_persistent_weak(self):
        """趋势在改善时，偏弱比例高也降级为 FLUCTUATING。"""
        ev = EvidenceInput(
            theme=DevTheme.IMITATION_TURN,
            record_count_14d=5, record_count_7d=3, scene_count=2,
            positive_count=1, weak_count=4,  # 80% 偏弱
            previous_weak_ratio=0.95,  # 上周 95% → 本周 80%
        )
        result = assess_theme_status(ev)
        assert result.status == DevStatus.FLUCTUATING  # 保护降级
        assert result.trend_direction == "improving"


# ---------------------------------------------------------------------------
# V2.0 新增：家长困扰度差异化测试
# ---------------------------------------------------------------------------


class TestParentDistress:
    """V2.0 家长困扰度差异化处理。"""

    def test_high_distress_boosts_stable_to_attention(self):
        """持续高困扰 + 稳定表现 → ATTENTION。"""
        ev = EvidenceInput(
            theme=DevTheme.ATTACHMENT_SECURITY,
            record_count_14d=6, record_count_7d=3, scene_count=3,
            positive_count=5, weak_count=1,
            distress_level="high",
            distress_duration_weeks=3,
        )
        result = assess_theme_status(ev)
        assert result.status == DevStatus.STABLE
        assert result.risk_level == RiskLevel.ATTENTION
        assert "困扰" in result.parent_distress_note

    def test_high_distress_boosts_persistent_weak_to_consult(self):
        """持续高困扰 + 持续偏弱 → CONSULT。"""
        ev = EvidenceInput(
            theme=DevTheme.SENSORY_PROCESSING,
            record_count_14d=5, record_count_7d=3, scene_count=2,
            positive_count=1, weak_count=4,
            distress_level="high",
            distress_duration_weeks=2,
        )
        result = assess_theme_status(ev)
        assert result.status == DevStatus.PERSISTENT_WEAK
        assert result.risk_level == RiskLevel.CONSULT

    def test_short_distress_no_boost(self):
        """高困扰但不足 2 周 → 不升级。"""
        ev = EvidenceInput(
            theme=DevTheme.EMOTION_TRANSITION,
            record_count_14d=6, record_count_7d=3, scene_count=3,
            positive_count=5, weak_count=1,
            distress_level="high",
            distress_duration_weeks=1,
        )
        result = assess_theme_status(ev)
        assert result.status == DevStatus.STABLE
        assert result.risk_level == RiskLevel.NORMAL


# ---------------------------------------------------------------------------
# V2.0 新增：新主题可用于趋势引擎
# ---------------------------------------------------------------------------


class TestNewThemesInEngine:
    """V2.0 新主题（感觉处理、依恋安全）可用于趋势引擎。"""

    def test_sensory_processing_assessment(self):
        """感觉处理主题能正常评估。"""
        ev = EvidenceInput(
            theme=DevTheme.SENSORY_PROCESSING,
            record_count_14d=5, record_count_7d=3, scene_count=2,
            positive_count=4, weak_count=1,
        )
        result = assess_theme_status(ev)
        assert result.theme == DevTheme.SENSORY_PROCESSING
        assert result.status == DevStatus.STABLE

    def test_attachment_security_assessment(self):
        """依恋安全主题能正常评估。"""
        ev = EvidenceInput(
            theme=DevTheme.ATTACHMENT_SECURITY,
            record_count_14d=5, record_count_7d=3, scene_count=2,
            positive_count=2, weak_count=3,
        )
        result = assess_theme_status(ev)
        assert result.theme == DevTheme.ATTACHMENT_SECURITY
        assert result.status == DevStatus.FLUCTUATING
