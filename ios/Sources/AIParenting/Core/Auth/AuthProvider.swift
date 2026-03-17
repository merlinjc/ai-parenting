import Foundation

/// 认证提供者协议
///
/// 为 APIClient 提供认证 Header，并管理登录状态。
/// 支持 JWT Bearer token 和 X-User-Id header 两种模式。
/// 所有实现须满足 Sendable 以支持并发。
public protocol AuthProvider: Sendable {

    /// 当前用户 ID（未登录时为 nil）
    var currentUserId: UUID? { get }

    /// 认证请求头（注入到每个 API 请求）
    var authHeaders: [String: String] { get }

    /// 是否已完成登录认证
    var isAuthenticated: Bool { get }
}
