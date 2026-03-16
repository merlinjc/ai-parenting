import Foundation

/// 认证提供者协议
///
/// 为 APIClient 提供认证 Header。当前使用 X-User-Id header，
/// 后续替换为 JWT Bearer token。所有实现须满足 Sendable 以支持并发。
public protocol AuthProvider: Sendable {

    /// 当前用户 ID
    var currentUserId: UUID { get }

    /// 认证请求头（注入到每个 API 请求）
    var authHeaders: [String: String] { get }
}
