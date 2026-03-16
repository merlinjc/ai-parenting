import Foundation

// MARK: - Request Models

/// 创建儿童档案请求
public struct ChildCreate: Codable, Sendable {
    public let nickname: String
    public let birthYearMonth: String
    public var focusThemes: [String]
    public var riskLevel: String

    public init(nickname: String, birthYearMonth: String, focusThemes: [String] = [], riskLevel: String = "normal") {
        self.nickname = nickname
        self.birthYearMonth = birthYearMonth
        self.focusThemes = focusThemes
        self.riskLevel = riskLevel
    }
}

/// 更新儿童档案请求
public struct ChildUpdate: Codable, Sendable {
    public var nickname: String?
    public var focusThemes: [String]?
    public var riskLevel: String?

    public init(nickname: String? = nil, focusThemes: [String]? = nil, riskLevel: String? = nil) {
        self.nickname = nickname
        self.focusThemes = focusThemes
        self.riskLevel = riskLevel
    }
}

// MARK: - Response Models

/// 儿童档案响应
public struct ChildResponse: Codable, Sendable, Identifiable {
    public let id: UUID
    public let userId: UUID
    public let nickname: String
    public let birthYearMonth: String
    public let ageMonths: Int
    public let stage: String
    public let focusThemes: [String]?
    public let riskLevel: String
    public let onboardingCompleted: Bool
    public let createdAt: Date
    public let updatedAt: Date

    public init(id: UUID, userId: UUID, nickname: String, birthYearMonth: String, ageMonths: Int, stage: String, focusThemes: [String]?, riskLevel: String, onboardingCompleted: Bool, createdAt: Date, updatedAt: Date) {
        self.id = id
        self.userId = userId
        self.nickname = nickname
        self.birthYearMonth = birthYearMonth
        self.ageMonths = ageMonths
        self.stage = stage
        self.focusThemes = focusThemes
        self.riskLevel = riskLevel
        self.onboardingCompleted = onboardingCompleted
        self.createdAt = createdAt
        self.updatedAt = updatedAt
    }
}
