import Foundation

/// 临时认证实现
///
/// 返回固定 UUID 的 X-User-Id header，与后端临时鉴权方案对齐。
/// 后续 JWT 实现只需使用 `JWTAuthProvider` 替换此类，不影响 APIClient。
public struct MockAuthProvider: AuthProvider {

    /// 固定的测试用户 ID（与后端默认值一致）
    public let currentUserId: UUID? = UUID(uuidString: "00000000-0000-0000-0000-000000000001")!

    public var authHeaders: [String: String] {
        ["X-User-Id": currentUserId!.uuidString]
    }

    /// Mock 模式下始终视为已认证
    public var isAuthenticated: Bool { true }

    public init() {}
}
