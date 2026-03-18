"""测试：枚举体系重构——DevTheme、InterventionFocus、DevStatus。"""

from ai_parenting.models.enums import (
    ChildStage,
    DevStatus,
    DevTheme,
    FocusTheme,
    InterventionFocus,
    RiskLevel,
)


class TestDevTheme:
    """六个一级发展主题。"""

    def test_all_six_themes(self):
        assert len(DevTheme) == 6

    def test_theme_values(self):
        expected = {
            "joint_attention", "expression_need", "imitation_turn",
            "emotion_transition", "social_approach", "play_narrative",
        }
        assert {t.value for t in DevTheme} == expected

    def test_display_name(self):
        assert DevTheme.JOINT_ATTENTION.display_name == "共同注意与社交回应"
        assert DevTheme.PLAY_NARRATIVE.display_name == "游戏、象征与叙事整合"

    def test_short_name(self):
        assert DevTheme.EXPRESSION_NEED.short_name == "表达需求"

    def test_observation_question(self):
        assert "会不会看" in DevTheme.JOINT_ATTENTION.observation_question

    def test_intervention_focuses(self):
        focuses = DevTheme.EMOTION_TRANSITION.intervention_focuses()
        assert InterventionFocus.TRANSITION_PREP in focuses
        assert InterventionFocus.EMOTION_NAMING in focuses
        assert len(focuses) == 2


class TestInterventionFocus:
    """八类干预焦点。"""

    def test_all_eight_focuses(self):
        assert len(InterventionFocus) == 8

    def test_focus_values(self):
        expected = {
            "wait_respond", "choice_express", "action_imitate", "turn_scaffold",
            "transition_prep", "emotion_naming", "social_rehearse", "narrative_scaffold",
        }
        assert {f.value for f in InterventionFocus} == expected

    def test_display_name(self):
        assert InterventionFocus.WAIT_RESPOND.display_name == "等待回应"
        assert InterventionFocus.NARRATIVE_SCAFFOLD.display_name == "叙事支架"

    def test_primary_theme(self):
        assert InterventionFocus.WAIT_RESPOND.primary_theme == DevTheme.JOINT_ATTENTION
        assert InterventionFocus.CHOICE_EXPRESS.primary_theme == DevTheme.EXPRESSION_NEED
        assert InterventionFocus.ACTION_IMITATE.primary_theme == DevTheme.IMITATION_TURN
        assert InterventionFocus.TURN_SCAFFOLD.primary_theme == DevTheme.IMITATION_TURN
        assert InterventionFocus.TRANSITION_PREP.primary_theme == DevTheme.EMOTION_TRANSITION
        assert InterventionFocus.EMOTION_NAMING.primary_theme == DevTheme.EMOTION_TRANSITION
        assert InterventionFocus.SOCIAL_REHEARSE.primary_theme == DevTheme.SOCIAL_APPROACH
        assert InterventionFocus.NARRATIVE_SCAFFOLD.primary_theme == DevTheme.PLAY_NARRATIVE


class TestDevStatus:
    """五级内部发展状态。"""

    def test_all_five_statuses(self):
        assert len(DevStatus) == 5

    def test_display_name(self):
        assert DevStatus.STABLE.display_name == "稳定出现"
        assert DevStatus.REGRESSING.display_name == "出现退步"

    def test_front_display(self):
        assert "继续在日常中巩固" in DevStatus.STABLE.front_display
        assert "咨询专业人员" in DevStatus.REGRESSING.front_display

    def test_to_risk_level(self):
        assert DevStatus.STABLE.to_risk_level() == RiskLevel.NORMAL
        assert DevStatus.FLUCTUATING.to_risk_level() == RiskLevel.NORMAL
        assert DevStatus.PERSISTENT_WEAK.to_risk_level() == RiskLevel.ATTENTION
        assert DevStatus.REGRESSING.to_risk_level() == RiskLevel.CONSULT
        assert DevStatus.INSUFFICIENT.to_risk_level() == RiskLevel.NORMAL


class TestFocusThemeLegacyMapping:
    """FocusTheme 向后兼容映射。"""

    def test_legacy_enum_still_works(self):
        assert FocusTheme.LANGUAGE.value == "language"
        assert len(FocusTheme) == 6

    def test_display_name(self):
        assert FocusTheme.LANGUAGE.display_name == "语言发展"

    def test_to_dev_themes(self):
        themes = FocusTheme.LANGUAGE.to_dev_themes()
        assert DevTheme.EXPRESSION_NEED in themes
        assert DevTheme.JOINT_ATTENTION in themes

    def test_emotion_mapping(self):
        themes = FocusTheme.EMOTION.to_dev_themes()
        assert themes == [DevTheme.EMOTION_TRANSITION]


class TestChildStageEnhancements:
    """ChildStage 增强属性。"""

    def test_display_name(self):
        assert "互动基础建立期" in ChildStage.M18_24.display_name
        assert "表达扩展" in ChildStage.M24_36.display_name
        assert "叙事整合" in ChildStage.M36_48.display_name


class TestRiskLevelEnhancements:
    """RiskLevel 增强属性。"""

    def test_display_name(self):
        assert RiskLevel.NORMAL.display_name == "正常波动"
        assert RiskLevel.ATTENTION.display_name == "重点关注"
        assert RiskLevel.CONSULT.display_name == "建议咨询"
