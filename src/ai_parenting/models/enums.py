"""枚举定义。

所有枚举值与设计文档严格对齐：
- ChildStage: 18_24m / 24_36m / 36_48m
- RiskLevel: normal / attention / consult
- DevTheme: 八个一级发展主题（观测维度）V2.0 新增感觉处理 + 依恋安全
- InterventionFocus: 十类干预焦点（行动维度）V2.0 新增感觉调节 + 安全基地
- DevStatus: 五级内部发展状态
- FocusTheme: 保留向后兼容，映射到 DevTheme
- SessionType: instant_help / plan_generation / weekly_feedback
- SessionStatus: pending / processing / completed / failed / degraded
- CompletionStatus: pending / executed / partial / needs_record
- DecisionValue: continue / lower_difficulty / change_focus
- MessageType: plan_reminder / record_prompt / weekly_feedback_ready / risk_alert / system
- ReadStatus: unread / read / processed
- PushStatus: pending / sent / delivered / failed
- FeedbackStatus: generating / ready / failed / viewed / decided
"""

from __future__ import annotations

from enum import Enum


class ChildStage(str, Enum):
    """儿童年龄阶段（三阶段划分）。"""

    M18_24 = "18_24m"
    M24_36 = "24_36m"
    M36_48 = "36_48m"

    @property
    def display_name(self) -> str:
        """中文显示名称。"""
        return _STAGE_DISPLAY[self]


_STAGE_DISPLAY = {
    ChildStage.M18_24: "18—24 个月（互动基础建立期）",
    ChildStage.M24_36: "24—36 个月（表达扩展与规则萌芽期）",
    ChildStage.M36_48: "36—48 个月（叙事整合与社会化准备期）",
}


class RiskLevel(str, Enum):
    """风险层级（三级分层）。"""

    NORMAL = "normal"
    ATTENTION = "attention"
    CONSULT = "consult"

    @property
    def display_name(self) -> str:
        """中文显示名称。"""
        return _RISK_DISPLAY[self]


_RISK_DISPLAY = {
    RiskLevel.NORMAL: "正常波动",
    RiskLevel.ATTENTION: "重点关注",
    RiskLevel.CONSULT: "建议咨询",
}


# ---------------------------------------------------------------------------
# 八个一级发展主题（观测维度）—— V2.0 从六个扩展为八个
# 来源：观测模型结构稿 V1.1 第三章 + V2.0 感觉处理与依恋安全补充
# ---------------------------------------------------------------------------


class DevTheme(str, Enum):
    """八个一级发展主题（观测维度）。

    V1: 六个核心可干预主题
    V2.0 新增:
    - SENSORY_PROCESSING: 感觉处理与调节——不使用学科术语，聚焦日常可观察行为
    - ATTACHMENT_SECURITY: 依恋安全与基地行为——不使用诊断标签，聚焦安全基地循环

    前台家长端入口仍可展示为更通俗的维度，但系统内部使用本枚举做主题判断。
    """

    JOINT_ATTENTION = "joint_attention"        # 共同注意与社交回应
    EXPRESSION_NEED = "expression_need"        # 表达需求与语言理解
    IMITATION_TURN = "imitation_turn"          # 模仿、轮流与互动节奏
    EMOTION_TRANSITION = "emotion_transition"  # 情绪过渡与共同调节
    SOCIAL_APPROACH = "social_approach"        # 社交接近与规则适应
    PLAY_NARRATIVE = "play_narrative"          # 游戏、象征与叙事整合
    # V2.0 新增
    SENSORY_PROCESSING = "sensory_processing"  # 感觉处理与调节
    ATTACHMENT_SECURITY = "attachment_security"  # 依恋安全与基地行为

    @property
    def display_name(self) -> str:
        """中文显示名称。"""
        return _DEV_THEME_DISPLAY[self]

    @property
    def short_name(self) -> str:
        """短名称，用于标签和列表。"""
        return _DEV_THEME_SHORT[self]

    @property
    def observation_question(self) -> str:
        """主要观察问题。"""
        return _DEV_THEME_QUESTION[self]

    def intervention_focuses(self) -> list[InterventionFocus]:
        """返回该主题下的干预焦点列表。"""
        return _THEME_TO_FOCUSES.get(self, [])


_DEV_THEME_DISPLAY = {
    DevTheme.JOINT_ATTENTION: "共同注意与社交回应",
    DevTheme.EXPRESSION_NEED: "表达需求与语言理解",
    DevTheme.IMITATION_TURN: "模仿、轮流与互动节奏",
    DevTheme.EMOTION_TRANSITION: "情绪过渡与共同调节",
    DevTheme.SOCIAL_APPROACH: "社交接近与规则适应",
    DevTheme.PLAY_NARRATIVE: "游戏、象征与叙事整合",
    DevTheme.SENSORY_PROCESSING: "感觉处理与调节",
    DevTheme.ATTACHMENT_SECURITY: "依恋安全与基地行为",
}

_DEV_THEME_SHORT = {
    DevTheme.JOINT_ATTENTION: "共同注意",
    DevTheme.EXPRESSION_NEED: "表达需求",
    DevTheme.IMITATION_TURN: "模仿轮流",
    DevTheme.EMOTION_TRANSITION: "情绪过渡",
    DevTheme.SOCIAL_APPROACH: "社交规则",
    DevTheme.PLAY_NARRATIVE: "游戏叙事",
    DevTheme.SENSORY_PROCESSING: "感觉调节",
    DevTheme.ATTACHMENT_SECURITY: "依恋安全",
}

_DEV_THEME_QUESTION = {
    DevTheme.JOINT_ATTENTION: "会不会看、回应、分享关注点",
    DevTheme.EXPRESSION_NEED: "会不会表达想要什么、听懂简单要求",
    DevTheme.IMITATION_TURN: "会不会模仿、接轮次、维持互动",
    DevTheme.EMOTION_TRANSITION: "遇到转换和受挫时如何反应",
    DevTheme.SOCIAL_APPROACH: "会不会接近人、参与规则、适应社交",
    DevTheme.PLAY_NARRATIVE: "会不会假装、讲述、串联经验",
    DevTheme.SENSORY_PROCESSING: "面对不同感觉体验时，如何反应和调整",
    DevTheme.ATTACHMENT_SECURITY: "和主要照护者之间的安全感如何表现",
}


# ---------------------------------------------------------------------------
# 十类干预焦点（行动维度）—— V2.0 从八类扩展为十类
# 来源：7 天微计划模板 V1 第八章 + V2.0 感觉调节与安全基地补充
# ---------------------------------------------------------------------------


class InterventionFocus(str, Enum):
    """十类干预焦点（行动维度）。

    每个焦点是可填入 7 天微计划统一模板的一种标准计划骨架。
    V2.0 新增:
    - SENSORY_MODULATE: 感觉调节——帮助孩子在日常中适应不同感觉体验
    - SECURE_BASE: 安全基地——在分离和重聚时建立安全感
    """

    WAIT_RESPOND = "wait_respond"          # 等待回应
    CHOICE_EXPRESS = "choice_express"      # 选择表达
    ACTION_IMITATE = "action_imitate"      # 动作模仿
    TURN_SCAFFOLD = "turn_scaffold"        # 轮流支架
    TRANSITION_PREP = "transition_prep"    # 过渡预告
    EMOTION_NAMING = "emotion_naming"      # 情绪命名
    SOCIAL_REHEARSE = "social_rehearse"    # 社交预演
    NARRATIVE_SCAFFOLD = "narrative_scaffold"  # 叙事支架
    # V2.0 新增
    SENSORY_MODULATE = "sensory_modulate"  # 感觉调节
    SECURE_BASE = "secure_base"            # 安全基地

    @property
    def display_name(self) -> str:
        """中文显示名称。"""
        return _INTERVENTION_DISPLAY[self]

    @property
    def primary_theme(self) -> DevTheme:
        """返回该焦点所属的主要发展主题。"""
        return _FOCUS_TO_THEME[self]


_INTERVENTION_DISPLAY = {
    InterventionFocus.WAIT_RESPOND: "等待回应",
    InterventionFocus.CHOICE_EXPRESS: "选择表达",
    InterventionFocus.ACTION_IMITATE: "动作模仿",
    InterventionFocus.TURN_SCAFFOLD: "轮流支架",
    InterventionFocus.TRANSITION_PREP: "过渡预告",
    InterventionFocus.EMOTION_NAMING: "情绪命名",
    InterventionFocus.SOCIAL_REHEARSE: "社交预演",
    InterventionFocus.NARRATIVE_SCAFFOLD: "叙事支架",
    InterventionFocus.SENSORY_MODULATE: "感觉调节",
    InterventionFocus.SECURE_BASE: "安全基地",
}

# 焦点 → 主题映射
_FOCUS_TO_THEME = {
    InterventionFocus.WAIT_RESPOND: DevTheme.JOINT_ATTENTION,
    InterventionFocus.CHOICE_EXPRESS: DevTheme.EXPRESSION_NEED,
    InterventionFocus.ACTION_IMITATE: DevTheme.IMITATION_TURN,
    InterventionFocus.TURN_SCAFFOLD: DevTheme.IMITATION_TURN,
    InterventionFocus.TRANSITION_PREP: DevTheme.EMOTION_TRANSITION,
    InterventionFocus.EMOTION_NAMING: DevTheme.EMOTION_TRANSITION,
    InterventionFocus.SOCIAL_REHEARSE: DevTheme.SOCIAL_APPROACH,
    InterventionFocus.NARRATIVE_SCAFFOLD: DevTheme.PLAY_NARRATIVE,
    InterventionFocus.SENSORY_MODULATE: DevTheme.SENSORY_PROCESSING,
    InterventionFocus.SECURE_BASE: DevTheme.ATTACHMENT_SECURITY,
}

# 主题 → 焦点列表映射
_THEME_TO_FOCUSES = {
    DevTheme.JOINT_ATTENTION: [InterventionFocus.WAIT_RESPOND],
    DevTheme.EXPRESSION_NEED: [InterventionFocus.CHOICE_EXPRESS],
    DevTheme.IMITATION_TURN: [InterventionFocus.ACTION_IMITATE, InterventionFocus.TURN_SCAFFOLD],
    DevTheme.EMOTION_TRANSITION: [InterventionFocus.TRANSITION_PREP, InterventionFocus.EMOTION_NAMING],
    DevTheme.SOCIAL_APPROACH: [InterventionFocus.SOCIAL_REHEARSE],
    DevTheme.PLAY_NARRATIVE: [InterventionFocus.NARRATIVE_SCAFFOLD],
    DevTheme.SENSORY_PROCESSING: [InterventionFocus.SENSORY_MODULATE],
    DevTheme.ATTACHMENT_SECURITY: [InterventionFocus.SECURE_BASE],
}


# ---------------------------------------------------------------------------
# 五级内部发展状态 —— 来源：观测模型结构稿 V1.1 第八章
# ---------------------------------------------------------------------------


class DevStatus(str, Enum):
    """五级内部发展状态。

    后台用于精细化表征主题状态，前台映射为三级风险层级（RiskLevel）。
    """

    STABLE = "stable"                    # 稳定出现
    FLUCTUATING = "fluctuating"          # 偶有波动
    PERSISTENT_WEAK = "persistent_weak"  # 持续偏弱
    REGRESSING = "regressing"            # 出现退步
    INSUFFICIENT = "insufficient"        # 待补充观察

    @property
    def display_name(self) -> str:
        """中文显示名称。"""
        return _DEV_STATUS_DISPLAY[self]

    @property
    def front_display(self) -> str:
        """前台家长看到的克制话术。"""
        return _DEV_STATUS_FRONT[self]

    def to_risk_level(self) -> RiskLevel:
        """映射为前台三级风险层级。"""
        return _STATUS_TO_RISK[self]


_DEV_STATUS_DISPLAY = {
    DevStatus.STABLE: "稳定出现",
    DevStatus.FLUCTUATING: "偶有波动",
    DevStatus.PERSISTENT_WEAK: "持续偏弱",
    DevStatus.REGRESSING: "出现退步",
    DevStatus.INSUFFICIENT: "待补充观察",
}

_DEV_STATUS_FRONT = {
    DevStatus.STABLE: "近期表现较稳定，可继续在日常中巩固",
    DevStatus.FLUCTUATING: "属于阶段内常见波动，建议继续观察",
    DevStatus.PERSISTENT_WEAK: "建议重点关注，并增加相应支持机会",
    DevStatus.REGRESSING: "建议尽快补充观察，并考虑咨询专业人员",
    DevStatus.INSUFFICIENT: "当前依据不足，请继续记录真实场景",
}

_STATUS_TO_RISK = {
    DevStatus.STABLE: RiskLevel.NORMAL,
    DevStatus.FLUCTUATING: RiskLevel.NORMAL,
    DevStatus.PERSISTENT_WEAK: RiskLevel.ATTENTION,
    DevStatus.REGRESSING: RiskLevel.CONSULT,
    DevStatus.INSUFFICIENT: RiskLevel.NORMAL,  # 证据不足不升级
}


# ---------------------------------------------------------------------------
# FocusTheme（向后兼容）—— 保留原有枚举值，添加映射方法
# ---------------------------------------------------------------------------


class FocusTheme(str, Enum):
    """关注主题（六大主题）—— 向后兼容枚举。

    V1 使用的学科分类枚举。新代码应优先使用 DevTheme（观测维度）
    和 InterventionFocus（行动维度）。FocusTheme 保留用于：
    - 数据库中 children.focus_themes 和 plans.focus_theme 字段
    - iOS/前端已有的 API 接口
    - 存量数据兼容

    通过 to_dev_theme() 可映射到新的发展主题体系。
    """

    LANGUAGE = "language"
    SOCIAL = "social"
    EMOTION = "emotion"
    MOTOR = "motor"
    COGNITION = "cognition"
    SELF_CARE = "self_care"

    @property
    def display_name(self) -> str:
        """中文显示名称。"""
        return _FOCUS_THEME_DISPLAY[self]

    def to_dev_themes(self) -> list[DevTheme]:
        """映射到新的发展主题体系（一个旧主题可能对应多个新主题）。"""
        return _LEGACY_TO_DEV_THEMES.get(self, [])


_FOCUS_THEME_DISPLAY = {
    FocusTheme.LANGUAGE: "语言发展",
    FocusTheme.SOCIAL: "社交能力",
    FocusTheme.EMOTION: "情绪管理",
    FocusTheme.MOTOR: "运动发展",
    FocusTheme.COGNITION: "认知发展",
    FocusTheme.SELF_CARE: "自理能力",
}

# 旧枚举 → 新主题映射（一对多）
_LEGACY_TO_DEV_THEMES = {
    FocusTheme.LANGUAGE: [DevTheme.EXPRESSION_NEED, DevTheme.JOINT_ATTENTION],
    FocusTheme.SOCIAL: [DevTheme.SOCIAL_APPROACH, DevTheme.JOINT_ATTENTION, DevTheme.ATTACHMENT_SECURITY],
    FocusTheme.EMOTION: [DevTheme.EMOTION_TRANSITION, DevTheme.ATTACHMENT_SECURITY],
    FocusTheme.MOTOR: [DevTheme.IMITATION_TURN, DevTheme.SENSORY_PROCESSING],
    FocusTheme.COGNITION: [DevTheme.PLAY_NARRATIVE],
    FocusTheme.SELF_CARE: [DevTheme.SOCIAL_APPROACH, DevTheme.SENSORY_PROCESSING],
}


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
