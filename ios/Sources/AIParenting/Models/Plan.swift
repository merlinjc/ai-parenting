import Foundation

// MARK: - Request Models

/// 创建微计划请求
public struct PlanCreateRequest: Codable, Sendable {
    public let childId: UUID

    public init(childId: UUID) {
        self.childId = childId
    }
}

/// 日任务完成状态更新
public struct DayTaskCompletionUpdate: Codable, Sendable {
    public let completionStatus: String

    public init(completionStatus: String) {
        self.completionStatus = completionStatus
    }
}

/// 追加关注内容到计划请求（「加入本周关注」功能）
public struct PlanFocusNoteUpdate: Codable, Sendable {
    public let note: String

    public init(note: String) {
        self.note = note
    }
}

// MARK: - Response Models

/// 日任务响应
public struct DayTaskResponse: Codable, Sendable, Identifiable {
    public let id: UUID
    public let planId: UUID
    public let dayNumber: Int
    public let mainExerciseTitle: String
    public let mainExerciseDescription: String
    public let naturalEmbedTitle: String
    public let naturalEmbedDescription: String
    public let demoScript: String
    public let observationPoint: String
    public var completionStatus: String
    public let completedAt: Date?

    public init(id: UUID, planId: UUID, dayNumber: Int, mainExerciseTitle: String, mainExerciseDescription: String, naturalEmbedTitle: String, naturalEmbedDescription: String, demoScript: String, observationPoint: String, completionStatus: String, completedAt: Date?) {
        self.id = id
        self.planId = planId
        self.dayNumber = dayNumber
        self.mainExerciseTitle = mainExerciseTitle
        self.mainExerciseDescription = mainExerciseDescription
        self.naturalEmbedTitle = naturalEmbedTitle
        self.naturalEmbedDescription = naturalEmbedDescription
        self.demoScript = demoScript
        self.observationPoint = observationPoint
        self.completionStatus = completionStatus  // var property for optimistic update
        self.completedAt = completedAt
    }
}

/// 微计划响应
public struct PlanResponse: Codable, Sendable, Identifiable {
    public let id: UUID
    public let childId: UUID
    public let version: Int
    public let status: String
    public let title: String
    public let primaryGoal: String
    public let focusTheme: String
    public let priorityScenes: [String]?
    public let stage: String
    public let riskLevelAtCreation: String
    public let startDate: Date
    public let endDate: Date
    public let currentDay: Int
    public let completionRate: Double
    public let observationCandidates: AnyCodable?
    public let nextWeekContext: String?
    public let nextWeekDirection: String?
    public let weekendReviewPrompt: String?
    public let conservativeNote: String?
    public let aiGenerationId: UUID?
    public let createdAt: Date
    public let updatedAt: Date
    public var dayTasks: [DayTaskResponse]

    public init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        id = try container.decode(UUID.self, forKey: .id)
        childId = try container.decode(UUID.self, forKey: .childId)
        version = try container.decode(Int.self, forKey: .version)
        status = try container.decode(String.self, forKey: .status)
        title = try container.decode(String.self, forKey: .title)
        primaryGoal = try container.decode(String.self, forKey: .primaryGoal)
        focusTheme = try container.decode(String.self, forKey: .focusTheme)
        priorityScenes = try container.decodeIfPresent([String].self, forKey: .priorityScenes)
        stage = try container.decode(String.self, forKey: .stage)
        riskLevelAtCreation = try container.decode(String.self, forKey: .riskLevelAtCreation)
        startDate = try container.decode(Date.self, forKey: .startDate)
        endDate = try container.decode(Date.self, forKey: .endDate)
        currentDay = try container.decode(Int.self, forKey: .currentDay)
        completionRate = try container.decode(Double.self, forKey: .completionRate)
        observationCandidates = try container.decodeIfPresent(AnyCodable.self, forKey: .observationCandidates)
        nextWeekContext = try container.decodeIfPresent(String.self, forKey: .nextWeekContext)
        nextWeekDirection = try container.decodeIfPresent(String.self, forKey: .nextWeekDirection)
        weekendReviewPrompt = try container.decodeIfPresent(String.self, forKey: .weekendReviewPrompt)
        conservativeNote = try container.decodeIfPresent(String.self, forKey: .conservativeNote)
        aiGenerationId = try container.decodeIfPresent(UUID.self, forKey: .aiGenerationId)
        createdAt = try container.decode(Date.self, forKey: .createdAt)
        updatedAt = try container.decode(Date.self, forKey: .updatedAt)
        dayTasks = try container.decodeIfPresent([DayTaskResponse].self, forKey: .dayTasks) ?? []
    }

    private enum CodingKeys: String, CodingKey {
        case id, childId, version, status, title, primaryGoal, focusTheme
        case priorityScenes, stage, riskLevelAtCreation, startDate, endDate
        case currentDay, completionRate, observationCandidates, nextWeekContext
        case nextWeekDirection, weekendReviewPrompt, conservativeNote
        case aiGenerationId, createdAt, updatedAt, dayTasks
    }
}

/// 计划 + 周反馈状态
public struct PlanWithFeedbackStatus: Codable, Sendable {
    public let plan: PlanResponse
    public let weeklyFeedbackStatus: String?

    public init(plan: PlanResponse, weeklyFeedbackStatus: String?) {
        self.plan = plan
        self.weeklyFeedbackStatus = weeklyFeedbackStatus
    }
}

/// 计划列表响应（含分页）
public struct PlanListResponse: Codable, Sendable {
    public let plans: [PlanResponse]
    public let hasMore: Bool
    public let total: Int

    public init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        plans = try container.decodeIfPresent([PlanResponse].self, forKey: .plans) ?? []
        hasMore = try container.decodeIfPresent(Bool.self, forKey: .hasMore) ?? false
        total = try container.decodeIfPresent(Int.self, forKey: .total) ?? 0
    }

    private enum CodingKeys: String, CodingKey {
        case plans, hasMore, total
    }
}

// MARK: - AnyCodable Helper

/// 类型擦除的 Codable 包装，用于处理 dict/null 类型的 JSON 字段
public struct AnyCodable: Codable, Sendable {
    public let value: Any?

    public init(_ value: Any?) {
        self.value = value
    }

    public init(from decoder: Decoder) throws {
        let container = try decoder.singleValueContainer()
        if container.decodeNil() {
            self.value = nil
        } else if let dict = try? container.decode([String: AnyCodable].self) {
            self.value = dict.mapValues { $0.value }
        } else if let array = try? container.decode([AnyCodable].self) {
            self.value = array.map { $0.value }
        } else if let string = try? container.decode(String.self) {
            self.value = string
        } else if let int = try? container.decode(Int.self) {
            self.value = int
        } else if let double = try? container.decode(Double.self) {
            self.value = double
        } else if let bool = try? container.decode(Bool.self) {
            self.value = bool
        } else {
            self.value = nil
        }
    }

    public func encode(to encoder: Encoder) throws {
        var container = encoder.singleValueContainer()
        if value == nil {
            try container.encodeNil()
        } else if let string = value as? String {
            try container.encode(string)
        } else if let int = value as? Int {
            try container.encode(int)
        } else if let double = value as? Double {
            try container.encode(double)
        } else if let bool = value as? Bool {
            try container.encode(bool)
        } else if let dict = value as? [String: Any?] {
            let wrapped = dict.mapValues { AnyCodable($0) }
            try container.encode(wrapped)
        } else if let array = value as? [Any?] {
            let wrapped = array.map { AnyCodable($0) }
            try container.encode(wrapped)
        } else {
            try container.encodeNil()
        }
    }
}
