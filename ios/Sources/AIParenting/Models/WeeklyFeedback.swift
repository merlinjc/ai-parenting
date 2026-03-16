import Foundation

// MARK: - Request Models

/// 创建周反馈请求
public struct WeeklyFeedbackCreateRequest: Codable, Sendable {
    public let planId: UUID

    public init(planId: UUID) {
        self.planId = planId
    }
}

/// 提交周反馈决策请求
public struct WeeklyFeedbackDecisionRequest: Codable, Sendable {
    public let decision: String

    public init(decision: String) {
        self.decision = decision
    }
}

// MARK: - Response Models

/// 周反馈响应
public struct WeeklyFeedbackResponse: Codable, Sendable, Identifiable {
    public let id: UUID
    public let planId: UUID
    public let childId: UUID
    public let status: String
    public let positiveChanges: AnyCodable?
    public let opportunities: AnyCodable?
    public let summaryText: String?
    public let decisionOptions: AnyCodable?
    public let selectedDecision: String?
    public let conservativePathNote: String?
    public let recordCountThisWeek: Int
    public let completionRateThisWeek: Double
    public let aiGenerationId: UUID?
    public let errorInfo: String?
    public let createdAt: Date
    public let viewedAt: Date?
    public let decidedAt: Date?

    public init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        id = try container.decode(UUID.self, forKey: .id)
        planId = try container.decode(UUID.self, forKey: .planId)
        childId = try container.decode(UUID.self, forKey: .childId)
        status = try container.decode(String.self, forKey: .status)
        positiveChanges = try container.decodeIfPresent(AnyCodable.self, forKey: .positiveChanges)
        opportunities = try container.decodeIfPresent(AnyCodable.self, forKey: .opportunities)
        summaryText = try container.decodeIfPresent(String.self, forKey: .summaryText)
        decisionOptions = try container.decodeIfPresent(AnyCodable.self, forKey: .decisionOptions)
        selectedDecision = try container.decodeIfPresent(String.self, forKey: .selectedDecision)
        conservativePathNote = try container.decodeIfPresent(String.self, forKey: .conservativePathNote)
        recordCountThisWeek = try container.decodeIfPresent(Int.self, forKey: .recordCountThisWeek) ?? 0
        completionRateThisWeek = try container.decodeIfPresent(Double.self, forKey: .completionRateThisWeek) ?? 0.0
        aiGenerationId = try container.decodeIfPresent(UUID.self, forKey: .aiGenerationId)
        errorInfo = try container.decodeIfPresent(String.self, forKey: .errorInfo)
        createdAt = try container.decode(Date.self, forKey: .createdAt)
        viewedAt = try container.decodeIfPresent(Date.self, forKey: .viewedAt)
        decidedAt = try container.decodeIfPresent(Date.self, forKey: .decidedAt)
    }

    private enum CodingKeys: String, CodingKey {
        case id, planId, childId, status, positiveChanges, opportunities
        case summaryText, decisionOptions, selectedDecision, conservativePathNote
        case recordCountThisWeek, completionRateThisWeek, aiGenerationId
        case errorInfo, createdAt, viewedAt, decidedAt
    }
}
