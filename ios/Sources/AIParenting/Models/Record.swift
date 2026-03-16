import Foundation

// MARK: - Request Models

/// 创建观察记录请求
public struct RecordCreate: Codable, Sendable {
    public let childId: UUID
    public let type: String
    public var tags: [String]?
    public var content: String?
    public var voiceUrl: String?
    public var transcript: String?
    public var scene: String?
    public var timeOfDay: String?
    public var theme: String?
    public var sourcePlanId: UUID?
    public var sourceSessionId: UUID?

    public init(childId: UUID, type: String, tags: [String]? = nil, content: String? = nil, voiceUrl: String? = nil, transcript: String? = nil, scene: String? = nil, timeOfDay: String? = nil, theme: String? = nil, sourcePlanId: UUID? = nil, sourceSessionId: UUID? = nil) {
        self.childId = childId
        self.type = type
        self.tags = tags
        self.content = content
        self.voiceUrl = voiceUrl
        self.transcript = transcript
        self.scene = scene
        self.timeOfDay = timeOfDay
        self.theme = theme
        self.sourcePlanId = sourcePlanId
        self.sourceSessionId = sourceSessionId
    }
}

// MARK: - Response Models

/// 观察记录响应
public struct RecordResponse: Codable, Sendable, Identifiable {
    public let id: UUID
    public let childId: UUID
    public let type: String
    public let tags: [String]?
    public let content: String?
    public let voiceUrl: String?
    public let transcript: String?
    public let scene: String?
    public let timeOfDay: String?
    public let theme: String?
    public let sourcePlanId: UUID?
    public let sourceSessionId: UUID?
    public let syncedToPlan: Bool
    public let createdAt: Date

    public init(id: UUID, childId: UUID, type: String, tags: [String]?, content: String?, voiceUrl: String?, transcript: String?, scene: String?, timeOfDay: String?, theme: String?, sourcePlanId: UUID?, sourceSessionId: UUID?, syncedToPlan: Bool, createdAt: Date) {
        self.id = id
        self.childId = childId
        self.type = type
        self.tags = tags
        self.content = content
        self.voiceUrl = voiceUrl
        self.transcript = transcript
        self.scene = scene
        self.timeOfDay = timeOfDay
        self.theme = theme
        self.sourcePlanId = sourcePlanId
        self.sourceSessionId = sourceSessionId
        self.syncedToPlan = syncedToPlan
        self.createdAt = createdAt
    }
}

/// 记录列表响应（含分页）
public struct RecordListResponse: Codable, Sendable {
    public let records: [RecordResponse]
    public let hasMore: Bool
    public let total: Int

    public init(records: [RecordResponse], hasMore: Bool, total: Int) {
        self.records = records
        self.hasMore = hasMore
        self.total = total
    }
}
