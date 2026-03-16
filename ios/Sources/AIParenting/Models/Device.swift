import Foundation

// MARK: - Request Models

/// 设备注册/更新请求
public struct DeviceRegisterRequest: Codable, Sendable {
    public let pushToken: String?
    public let platform: String
    public let appVersion: String

    public init(pushToken: String? = nil, platform: String = "iOS", appVersion: String) {
        self.pushToken = pushToken
        self.platform = platform
        self.appVersion = appVersion
    }
}

// MARK: - Response Models

/// 设备响应
public struct DeviceResponse: Codable, Sendable, Identifiable {
    public let id: UUID
    public let userId: UUID
    public let pushToken: String?
    public let platform: String
    public let appVersion: String
    public let lastActiveAt: Date
    public let isActive: Bool

    public init(id: UUID, userId: UUID, pushToken: String?, platform: String, appVersion: String, lastActiveAt: Date, isActive: Bool) {
        self.id = id
        self.userId = userId
        self.pushToken = pushToken
        self.platform = platform
        self.appVersion = appVersion
        self.lastActiveAt = lastActiveAt
        self.isActive = isActive
    }
}
