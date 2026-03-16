import Foundation

// MARK: - Response Models

/// 用户档案响应
public struct UserProfileResponse: Codable, Sendable, Identifiable {
    public let id: UUID
    public let displayName: String?
    public let caregiverRole: String?
    public let timezone: String
    public let pushEnabled: Bool
    public let createdAt: Date
    public let updatedAt: Date
    public let children: [ChildResponse]

    public init(id: UUID, displayName: String?, caregiverRole: String?, timezone: String, pushEnabled: Bool, createdAt: Date, updatedAt: Date, children: [ChildResponse]) {
        self.id = id
        self.displayName = displayName
        self.caregiverRole = caregiverRole
        self.timezone = timezone
        self.pushEnabled = pushEnabled
        self.createdAt = createdAt
        self.updatedAt = updatedAt
        self.children = children
    }
}

// MARK: - Request Models

/// 更新用户档案请求
public struct UserProfileUpdate: Codable, Sendable {
    public var displayName: String?
    public var caregiverRole: String?
    public var timezone: String?
    public var pushEnabled: Bool?

    public init(displayName: String? = nil, caregiverRole: String? = nil, timezone: String? = nil, pushEnabled: Bool? = nil) {
        self.displayName = displayName
        self.caregiverRole = caregiverRole
        self.timezone = timezone
        self.pushEnabled = pushEnabled
    }
}
