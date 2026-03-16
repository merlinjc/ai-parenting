import Foundation

/// 健康检查响应
public struct HealthResponse: Codable, Sendable {
    public let status: String
    public let version: String

    public init(status: String, version: String) {
        self.status = status
        self.version = version
    }
}
