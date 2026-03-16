"""枚举定义。

所有枚举值与设计文档严格对齐：
- ChildStage: 18_24m / 24_36m / 36_48m
- RiskLevel: normal / attention / consult
- FocusTheme: language / social / emotion / motor / cognition / self_care
- SessionType: instant_help / plan_generation / weekly_feedback
- SessionStatus: pending / processing / completed / failed / degraded
- CompletionStatus: pending / executed / partial / needs_record
- DecisionValue: continue / lower_difficulty / change_focus
- MessageType: plan_reminder / record_prompt / weekly_feedback_ready / risk_alert / system
- ReadStatus: unread / read / processed
- PushStatus: pending / sent / delivered / failed
- FeedbackStatus: generating / ready / failed / viewed / decided
"""

from enum import Enum


class ChildStage(str, Enum):
    """儿童年龄阶段（三阶段划分）。"""

    M18_24 = "18_24m"
    M24_36 = "24_36m"
    M36_48 = "36_48m"


class RiskLevel(str, Enum):
    """风险层级（三级分层）。"""

    NORMAL = "normal"
    ATTENTION = "attention"
    CONSULT = "consult"


class FocusTheme(str, Enum):
    """关注主题（六大主题）。"""

    LANGUAGE = "language"
    SOCIAL = "social"
    EMOTION = "emotion"
    MOTOR = "motor"
    COGNITION = "cognition"
    SELF_CARE = "self_care"


class SessionType(str, Enum):
    """AI 会话类型。"""

    INSTANT_HELP = "instant_help"
    PLAN_GENERATION = "plan_generation"
    WEEKLY_FEEDBACK = "weekly_feedback"


class SessionStatus(str, Enum):
    """AI 会话状态。"""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    DEGRADED = "degraded"


class CompletionStatus(str, Enum):
    """日任务完成状态。"""

    PENDING = "pending"
    EXECUTED = "executed"
    PARTIAL = "partial"
    NEEDS_RECORD = "needs_record"


class DecisionValue(str, Enum):
    """周反馈决策选项值。"""

    CONTINUE = "continue"
    LOWER_DIFFICULTY = "lower_difficulty"
    CHANGE_FOCUS = "change_focus"


class MessageType(str, Enum):
    """消息类型（五种触达类型）。"""

    PLAN_REMINDER = "plan_reminder"
    RECORD_PROMPT = "record_prompt"
    WEEKLY_FEEDBACK_READY = "weekly_feedback_ready"
    RISK_ALERT = "risk_alert"
    SYSTEM = "system"


class ReadStatus(str, Enum):
    """消息阅读状态。"""

    UNREAD = "unread"
    READ = "read"
    PROCESSED = "processed"


class PushStatus(str, Enum):
    """推送状态。"""

    PENDING = "pending"
    SENT = "sent"
    DELIVERED = "delivered"
    FAILED = "failed"


class FeedbackStatus(str, Enum):
    """周反馈状态。"""

    GENERATING = "generating"
    READY = "ready"
    FAILED = "failed"
    VIEWED = "viewed"
    DECIDED = "decided"
