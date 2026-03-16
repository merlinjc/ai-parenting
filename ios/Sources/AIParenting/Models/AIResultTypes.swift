import Foundation

// MARK: - AnyCodable 解码扩展

extension AnyCodable {
    /// 将 AnyCodable 的底层值安全解码为指定的 Decodable 类型。
    /// 内部先将 value 序列化为 JSON Data，再用 JSONDecoder 解码。
    /// 解析失败时返回 nil，绝不 crash。
    public func decode<T: Decodable>(as type: T.Type) -> T? {
        guard let value = self.value else { return nil }
        do {
            let data = try JSONSerialization.data(withJSONObject: value, options: [])
            let decoder = JSONDecoder()
            decoder.keyDecodingStrategy = .convertFromSnakeCase
            return try decoder.decode(T.self, from: data)
        } catch {
            return nil
        }
    }

    /// 将 AnyCodable 的底层值解码为字符串数组（常见的简单 JSON 数组场景）。
    public var stringArray: [String]? {
        value as? [String]
    }

    /// 将 AnyCodable 的底层值解码为字典（常见的 JSON object 场景）。
    public var dictionary: [String: Any]? {
        value as? [String: Any?] as? [String: Any]
    }
}

// MARK: - 即时求助结果结构

/// 三步支持结构中的单步内容（对齐后端 StepContent）
public struct StepContent: Codable, Sendable, Identifiable {
    public let title: String
    public let body: String
    public let exampleScript: String?

    public var id: String { title }

    public init(title: String, body: String, exampleScript: String? = nil) {
        self.title = title
        self.body = body
        self.exampleScript = exampleScript
    }
}

/// 即时求助完整输出结构（对齐后端 InstantHelpResult）
public struct InstantHelpResultContent: Codable, Sendable {
    public let stepOne: StepContent
    public let stepTwo: StepContent
    public let stepThree: StepContent
    public let scenarioSummary: String
    public let suggestRecord: Bool
    public let suggestAddFocus: Bool
    public let suggestConsultPrep: Bool
    public let consultPrepReason: String?
    public let boundaryNote: String

    public init(
        stepOne: StepContent,
        stepTwo: StepContent,
        stepThree: StepContent,
        scenarioSummary: String,
        suggestRecord: Bool,
        suggestAddFocus: Bool,
        suggestConsultPrep: Bool,
        consultPrepReason: String? = nil,
        boundaryNote: String
    ) {
        self.stepOne = stepOne
        self.stepTwo = stepTwo
        self.stepThree = stepThree
        self.scenarioSummary = scenarioSummary
        self.suggestRecord = suggestRecord
        self.suggestAddFocus = suggestAddFocus
        self.suggestConsultPrep = suggestConsultPrep
        self.consultPrepReason = consultPrepReason
        self.boundaryNote = boundaryNote
    }

    /// 三个步骤的有序数组，便于 ForEach 渲染
    public var steps: [StepContent] {
        [stepOne, stepTwo, stepThree]
    }

    /// 三步的标签名称（用于 UI 展示）
    public static let stepLabels = ["先稳住自己", "接下来做一个小动作", "没接住怎么办"]
}

// MARK: - 上下文快照

/// 儿童上下文快照（对齐后端 ContextSnapshot）
public struct ContextSnapshotContent: Codable, Sendable {
    public let childAgeMonths: Int
    public let childStage: String
    public let childFocusThemes: [String]?
    public let childRiskLevel: String
    public let activePlanId: String?
    public let activePlanDay: Int?
    public let recentRecordIds: [String]?
    public let recentRecordKeywords: [String]?

    public init(
        childAgeMonths: Int,
        childStage: String,
        childFocusThemes: [String]? = nil,
        childRiskLevel: String,
        activePlanId: String? = nil,
        activePlanDay: Int? = nil,
        recentRecordIds: [String]? = nil,
        recentRecordKeywords: [String]? = nil
    ) {
        self.childAgeMonths = childAgeMonths
        self.childStage = childStage
        self.childFocusThemes = childFocusThemes
        self.childRiskLevel = childRiskLevel
        self.activePlanId = activePlanId
        self.activePlanDay = activePlanDay
        self.recentRecordIds = recentRecordIds
        self.recentRecordKeywords = recentRecordKeywords
    }

    /// 格式化的阶段显示名称
    public var stageDisplayName: String {
        ChildStage(rawValue: childStage)?.displayName ?? childStage
    }

    /// 格式化的风险等级显示名称
    public var riskLevelDisplayName: String {
        RiskLevel(rawValue: childRiskLevel)?.displayName ?? childRiskLevel
    }

    /// 格式化的关注主题显示名称列表
    public var focusThemeDisplayNames: [String] {
        (childFocusThemes ?? []).compactMap { FocusTheme(rawValue: $0)?.displayName }
    }
}

// MARK: - 快速打点候选项

/// 快速打点候选项（对齐后端 ObservationCandidateContent）
public struct ObservationCandidateItem: Codable, Sendable, Identifiable {
    public let id: String
    public let text: String
    public let theme: String
    public let defaultSelected: Bool

    public init(id: String, text: String, theme: String, defaultSelected: Bool) {
        self.id = id
        self.text = text
        self.theme = theme
        self.defaultSelected = defaultSelected
    }

    /// 格式化的主题显示名称
    public var themeDisplayName: String {
        FocusTheme(rawValue: theme)?.displayName ?? theme
    }
}

// MARK: - 周反馈结构

/// 周反馈变化项（对齐后端 FeedbackItemContent）
public struct FeedbackChangeItem: Codable, Sendable, Identifiable {
    public let title: String
    public let description: String
    public let supportingEvidence: String?

    public var id: String { title }

    public init(title: String, description: String, supportingEvidence: String? = nil) {
        self.title = title
        self.description = description
        self.supportingEvidence = supportingEvidence
    }
}

/// 周反馈决策选项（对齐后端 DecisionOptionContent）
public struct DecisionOptionItem: Codable, Sendable, Identifiable {
    public let id: String
    public let text: String
    public let value: String
    public let rationale: String

    public init(id: String, text: String, value: String, rationale: String) {
        self.id = id
        self.text = text
        self.value = value
        self.rationale = rationale
    }

    /// 对应的 DecisionValue 枚举
    public var decisionValue: DecisionValue? {
        DecisionValue(rawValue: value)
    }
}

/// 周反馈完整输出结构（对齐后端 WeeklyFeedbackResult）
public struct WeeklyFeedbackResultContent: Codable, Sendable {
    public let positiveChanges: [FeedbackChangeItem]
    public let opportunities: [FeedbackChangeItem]
    public let summaryText: String
    public let decisionOptions: [DecisionOptionItem]
    public let conservativePathNote: String
    public let referencedRecordIds: [String]?
    public let referencedPlanId: String?

    public init(
        positiveChanges: [FeedbackChangeItem],
        opportunities: [FeedbackChangeItem],
        summaryText: String,
        decisionOptions: [DecisionOptionItem],
        conservativePathNote: String,
        referencedRecordIds: [String]? = nil,
        referencedPlanId: String? = nil
    ) {
        self.positiveChanges = positiveChanges
        self.opportunities = opportunities
        self.summaryText = summaryText
        self.decisionOptions = decisionOptions
        self.conservativePathNote = conservativePathNote
        self.referencedRecordIds = referencedRecordIds
        self.referencedPlanId = referencedPlanId
    }
}

// MARK: - 降级结果

/// AI 降级结果（当 AI 调用失败时使用通用安全文本）
public struct DegradedResultContent: Codable, Sendable {
    public let message: String?
    public let fallbackText: String?

    public init(message: String? = nil, fallbackText: String? = nil) {
        self.message = message
        self.fallbackText = fallbackText
    }

    /// 获取可展示的文本（优先 message，其次 fallbackText）
    public var displayText: String {
        message ?? fallbackText ?? "系统正在优化中，请稍后再试"
    }
}

// MARK: - 消息深链目标参数

/// 消息的深链目标参数解析
public struct MessageTargetParams: Codable, Sendable {
    public let planId: String?
    public let feedbackId: String?
    public let recordId: String?
    public let childId: String?

    public init(planId: String? = nil, feedbackId: String? = nil, recordId: String? = nil, childId: String? = nil) {
        self.planId = planId
        self.feedbackId = feedbackId
        self.recordId = recordId
        self.childId = childId
    }
}

// MARK: - 便捷解析扩展

extension AISessionResponse {
    /// 解析 result 为即时求助三步结构
    public var parsedResult: InstantHelpResultContent? {
        result?.decode(as: InstantHelpResultContent.self)
    }

    /// 解析 contextSnapshot 为上下文快照
    public var parsedContextSnapshot: ContextSnapshotContent? {
        contextSnapshot?.decode(as: ContextSnapshotContent.self)
    }

    /// 解析 degradedResult 为降级文本
    public var parsedDegradedResult: DegradedResultContent? {
        degradedResult?.decode(as: DegradedResultContent.self)
    }

    /// 判断是否为降级结果
    public var isDegraded: Bool {
        status == SessionStatus.degraded.rawValue
    }
}

extension PlanResponse {
    /// 解析 observationCandidates 为快速打点候选项数组
    public var parsedObservationCandidates: [ObservationCandidateItem] {
        observationCandidates?.decode(as: [ObservationCandidateItem].self) ?? []
    }
}

extension WeeklyFeedbackResponse {
    /// 解析 positiveChanges 为变化项数组
    public var parsedPositiveChanges: [FeedbackChangeItem] {
        positiveChanges?.decode(as: [FeedbackChangeItem].self) ?? []
    }

    /// 解析 opportunities 为机会项数组
    public var parsedOpportunities: [FeedbackChangeItem] {
        opportunities?.decode(as: [FeedbackChangeItem].self) ?? []
    }

    /// 解析 decisionOptions 为决策选项数组
    public var parsedDecisionOptions: [DecisionOptionItem] {
        decisionOptions?.decode(as: [DecisionOptionItem].self) ?? []
    }
}

extension MessageResponse {
    /// 解析 targetParams 为深链参数
    public var parsedTargetParams: MessageTargetParams? {
        targetParams?.decode(as: MessageTargetParams.self)
    }

    /// 是否为风险警报类型
    public var isRiskAlert: Bool {
        type == MessageType.riskAlert.rawValue
    }

    /// 是否为周反馈就绪通知
    public var isWeeklyFeedbackReady: Bool {
        type == MessageType.weeklyFeedbackReady.rawValue
    }
}
