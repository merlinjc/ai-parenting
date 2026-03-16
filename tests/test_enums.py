"""枚举值正确性测试。

验证所有枚举值与设计文档严格对齐。
"""

from ai_parenting.models.enums import (
    ChildStage,
    CompletionStatus,
    DecisionValue,
    FocusTheme,
    RiskLevel,
    SessionStatus,
    SessionType,
)


class TestChildStage:
    """ChildStage 枚举值必须与设计文档对齐：18_24m / 24_36m / 36_48m。"""

    def test_values(self):
        assert ChildStage.M18_24.value == "18_24m"
        assert ChildStage.M24_36.value == "24_36m"
        assert ChildStage.M36_48.value == "36_48m"

    def test_count(self):
        assert len(ChildStage) == 3

    def test_from_value(self):
        assert ChildStage("18_24m") is ChildStage.M18_24
        assert ChildStage("24_36m") is ChildStage.M24_36
        assert ChildStage("36_48m") is ChildStage.M36_48


class TestRiskLevel:
    """RiskLevel 枚举值必须对齐：normal / attention / consult。"""

    def test_values(self):
        assert RiskLevel.NORMAL.value == "normal"
        assert RiskLevel.ATTENTION.value == "attention"
        assert RiskLevel.CONSULT.value == "consult"

    def test_count(self):
        assert len(RiskLevel) == 3


class TestFocusTheme:
    """FocusTheme 枚举值必须覆盖六大主题。"""

    def test_values(self):
        assert FocusTheme.LANGUAGE.value == "language"
        assert FocusTheme.SOCIAL.value == "social"
        assert FocusTheme.EMOTION.value == "emotion"
        assert FocusTheme.MOTOR.value == "motor"
        assert FocusTheme.COGNITION.value == "cognition"
        assert FocusTheme.SELF_CARE.value == "self_care"

    def test_count(self):
        assert len(FocusTheme) == 6


class TestSessionType:
    """SessionType 枚举值。"""

    def test_values(self):
        assert SessionType.INSTANT_HELP.value == "instant_help"
        assert SessionType.PLAN_GENERATION.value == "plan_generation"
        assert SessionType.WEEKLY_FEEDBACK.value == "weekly_feedback"

    def test_count(self):
        assert len(SessionType) == 3


class TestSessionStatus:
    """SessionStatus 枚举值。"""

    def test_values(self):
        assert SessionStatus.PENDING.value == "pending"
        assert SessionStatus.PROCESSING.value == "processing"
        assert SessionStatus.COMPLETED.value == "completed"
        assert SessionStatus.FAILED.value == "failed"
        assert SessionStatus.DEGRADED.value == "degraded"

    def test_count(self):
        assert len(SessionStatus) == 5


class TestCompletionStatus:
    """CompletionStatus 枚举值。"""

    def test_values(self):
        assert CompletionStatus.PENDING.value == "pending"
        assert CompletionStatus.EXECUTED.value == "executed"
        assert CompletionStatus.PARTIAL.value == "partial"
        assert CompletionStatus.NEEDS_RECORD.value == "needs_record"

    def test_count(self):
        assert len(CompletionStatus) == 4


class TestDecisionValue:
    """DecisionValue 枚举值。"""

    def test_values(self):
        assert DecisionValue.CONTINUE.value == "continue"
        assert DecisionValue.LOWER_DIFFICULTY.value == "lower_difficulty"
        assert DecisionValue.CHANGE_FOCUS.value == "change_focus"

    def test_count(self):
        assert len(DecisionValue) == 3
