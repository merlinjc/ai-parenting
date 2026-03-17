import Foundation

// MARK: - Skill Models (Phase 3)

/// 技能信息（从后端 GET /skills 获取）
public struct SkillInfoResponse: Codable, Identifiable, Sendable {
    public let name: String
    public let displayName: String
    public let description: String
    public let version: String
    public let icon: String
    public let tags: [String]
    public let isEnabled: Bool
    public let sessionType: String?

    public var id: String { name }

    enum CodingKeys: String, CodingKey {
        case name
        case displayName = "display_name"
        case description
        case version
        case icon
        case tags
        case isEnabled = "is_enabled"
        case sessionType = "session_type"
    }
}

/// 技能列表响应
public struct SkillListResponse: Codable, Sendable {
    public let skills: [SkillInfoResponse]
    public let total: Int
}

/// 睡眠分析请求
///
/// 注意：APIClient 已全局启用 `keyEncodingStrategy = .convertToSnakeCase`，
/// 无需手动定义 CodingKeys。
public struct SleepAnalysisRequest: Codable, Sendable {
    public let childId: UUID
    public let sleepRecords: [[String: AnyCodableValue]]
}

/// 睡眠分析响应
///
/// 注意：APIClient 已全局启用 `keyDecodingStrategy = .convertFromSnakeCase`，
/// 无需手动定义 CodingKeys。
public struct SleepAnalysisResponse: Codable, Sendable {
    public let overallRating: String
    public let ratingDisplay: String
    public let avgTotalHours: Double
    public let avgNightWakings: Double
    public let bedtimeConsistency: String
    public let summaryText: String
    public let recommendations: [String]
    public let ageReference: String
}

// MARK: - AnyCodableValue

/// 通用可编码值（用于睡眠记录的灵活 dict 编码）
public enum AnyCodableValue: Codable, Sendable {
    case string(String)
    case int(Int)
    case double(Double)

    public init(from decoder: Decoder) throws {
        let container = try decoder.singleValueContainer()
        if let intVal = try? container.decode(Int.self) {
            self = .int(intVal)
        } else if let doubleVal = try? container.decode(Double.self) {
            self = .double(doubleVal)
        } else {
            self = .string(try container.decode(String.self))
        }
    }

    public func encode(to encoder: Encoder) throws {
        var container = encoder.singleValueContainer()
        switch self {
        case .string(let val): try container.encode(val)
        case .int(let val): try container.encode(val)
        case .double(let val): try container.encode(val)
        }
    }
}
