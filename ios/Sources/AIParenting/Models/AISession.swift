import Foundation

// MARK: - Request Models

/// 即时求助请求
public struct InstantHelpRequest: Codable, Sendable {
    public let childId: UUID
    public var scenario: String?
    public var inputText: String?
    public var planId: UUID?

    public init(childId: UUID, scenario: String? = nil, inputText: String? = nil, planId: UUID? = nil) {
        self.childId = childId
        self.scenario = scenario
        self.inputText = inputText
        self.planId = planId
    }
}

// MARK: - Response Models

/// AI 会话响应
public struct AISessionResponse: Codable, Sendable, Identifiable {
    public let id: UUID
    public let childId: UUID
    public let sessionType: String
    public let status: String
    public let inputScenario: String?
    public let inputText: String?
    public let contextSnapshot: AnyCodable?
    public let result: AnyCodable?
    public let errorInfo: String?
    public let degradedResult: AnyCodable?
    public let modelProvider: String?
    public let modelVersion: String?
    public let promptTemplateId: String?
    public let latencyMs: Int?
    public let retryCount: Int
    public let createdAt: Date
    public let completedAt: Date?

    public init(id: UUID, childId: UUID, sessionType: String, status: String, inputScenario: String?, inputText: String?, contextSnapshot: AnyCodable?, result: AnyCodable?, errorInfo: String?, degradedResult: AnyCodable?, modelProvider: String?, modelVersion: String?, promptTemplateId: String?, latencyMs: Int?, retryCount: Int, createdAt: Date, completedAt: Date?) {
        self.id = id
        self.childId = childId
        self.sessionType = sessionType
        self.status = status
        self.inputScenario = inputScenario
        self.inputText = inputText
        self.contextSnapshot = contextSnapshot
        self.result = result
        self.errorInfo = errorInfo
        self.degradedResult = degradedResult
        self.modelProvider = modelProvider
        self.modelVersion = modelVersion
        self.promptTemplateId = promptTemplateId
        self.latencyMs = latencyMs
        self.retryCount = retryCount
        self.createdAt = createdAt
        self.completedAt = completedAt
    }
}
