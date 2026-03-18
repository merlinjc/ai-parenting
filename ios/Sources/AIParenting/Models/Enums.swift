import Foundation

// MARK: - 业务枚举（与后端 enums.py 完全对齐）

/// 儿童年龄阶段
public enum ChildStage: String, Codable, Sendable, CaseIterable {
    case months18to24 = "18_24m"
    case months24to36 = "24_36m"
    case months36to48 = "36_48m"

    public var displayName: String {
        switch self {
        case .months18to24: return "18-24个月"
        case .months24to36: return "24-36个月"
        case .months36to48: return "36-48个月"
        }
    }
}

/// 风险层级
public enum RiskLevel: String, Codable, Sendable, CaseIterable {
    case normal
    case attention
    case consult

    public var displayName: String {
        switch self {
        case .normal: return "正常"
        case .attention: return "关注"
        case .consult: return "建议咨询"
        }
    }
}

/// 关注主题
///
/// V2.0 新增：sensoryProcessing（感觉处理与调节）、attachmentSecurity（依恋安全与基地行为）
/// 与后端 DevTheme 的 8 值体系对齐，同时保持对旧 6 值的向后兼容。
public enum FocusTheme: String, Codable, Sendable, CaseIterable {
    case language
    case social
    case emotion
    case motor
    case cognition
    case selfCare = "self_care"
    // V2.0 新增
    case sensoryProcessing = "sensory_processing"
    case attachmentSecurity = "attachment_security"

    public var displayName: String {
        switch self {
        case .language: return "语言"
        case .social: return "社交"
        case .emotion: return "情绪"
        case .motor: return "运动"
        case .cognition: return "认知"
        case .selfCare: return "自理"
        case .sensoryProcessing: return "感觉调节"
        case .attachmentSecurity: return "依恋安全"
        }
    }

    /// 主题图标（SF Symbols）
    public var iconName: String {
        switch self {
        case .language: return "mouth.fill"
        case .social: return "person.2.fill"
        case .emotion: return "heart.fill"
        case .motor: return "figure.run"
        case .cognition: return "brain.head.profile"
        case .selfCare: return "hands.sparkles.fill"
        case .sensoryProcessing: return "hand.raised.fingers.spread.fill"
        case .attachmentSecurity: return "figure.2.and.child.holdinghands"
        }
    }
}

/// AI 会话类型
public enum SessionType: String, Codable, Sendable {
    case instantHelp = "instant_help"
    case planGeneration = "plan_generation"
    case weeklyFeedback = "weekly_feedback"
}

/// AI 会话状态
public enum SessionStatus: String, Codable, Sendable {
    case pending
    case processing
    case completed
    case failed
    case degraded
}

/// 日任务完成状态
public enum CompletionStatus: String, Codable, Sendable, CaseIterable {
    case pending
    case executed
    case partial
    case needsRecord = "needs_record"

    public var displayName: String {
        switch self {
        case .pending: return "待执行"
        case .executed: return "已执行"
        case .partial: return "部分完成"
        case .needsRecord: return "待记录"
        }
    }
}

/// 周反馈决策选项
public enum DecisionValue: String, Codable, Sendable, CaseIterable {
    case `continue` = "continue"
    case lowerDifficulty = "lower_difficulty"
    case changeFocus = "change_focus"

    public var displayName: String {
        switch self {
        case .continue: return "继续当前方向"
        case .lowerDifficulty: return "降低难度"
        case .changeFocus: return "更换焦点"
        }
    }
}

/// 消息类型
public enum MessageType: String, Codable, Sendable {
    case planReminder = "plan_reminder"
    case recordPrompt = "record_prompt"
    case weeklyFeedbackReady = "weekly_feedback_ready"
    case riskAlert = "risk_alert"
    case system
}

/// 消息阅读状态
public enum ReadStatus: String, Codable, Sendable {
    case unread
    case read
    case processed
}

/// 推送状态
public enum PushStatus: String, Codable, Sendable {
    case pending
    case sent
    case delivered
    case failed
}

/// 周反馈状态
public enum FeedbackStatus: String, Codable, Sendable {
    case generating
    case ready
    case failed
    case viewed
    case decided
}

/// 记录类型
public enum RecordType: String, Codable, Sendable, CaseIterable {
    case quickCheck = "quick_check"
    case event
    case voice

    public var displayName: String {
        switch self {
        case .quickCheck: return "快速检查"
        case .event: return "事件记录"
        case .voice: return "语音记录"
        }
    }
}
