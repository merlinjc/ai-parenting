import Foundation

// MARK: - Memory Init

/// 记忆初始化请求
///
/// 注意：APIClient 已全局启用 `keyEncodingStrategy = .convertToSnakeCase`，
/// 无需手动定义 CodingKeys。
public struct MemoryInitRequest: Codable, Sendable {
    public let childId: UUID
    public let caregiverRole: String
    public let recentSituation: String

    public init(childId: UUID, caregiverRole: String, recentSituation: String = "") {
        self.childId = childId
        self.caregiverRole = caregiverRole
        self.recentSituation = recentSituation
    }
}

/// 记忆初始化响应
///
/// 注意：APIClient 已全局启用 `keyDecodingStrategy = .convertFromSnakeCase`，
/// 无需手动定义 CodingKeys。
public struct MemoryInitResponse: Codable, Sendable {
    public let success: Bool
    /// 初始化的记忆文件名 → 内容映射
    public let files: [String: String]
    public let message: String
}
