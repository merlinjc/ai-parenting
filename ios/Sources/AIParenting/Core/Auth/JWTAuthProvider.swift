import Foundation
import Security

/// JWT 认证提供者
///
/// 通过邮箱+密码登录获取 JWT Token，使用 Keychain 安全存储 Token。
/// 实现 AuthProvider 协议，为 APIClient 提供 Bearer Token Header。
public final class JWTAuthProvider: AuthProvider, @unchecked Sendable {

    // MARK: - Keychain Keys

    private static let tokenKey = "ai_parenting_jwt_token"
    private static let userIdKey = "ai_parenting_user_id"

    // MARK: - State

    private var _token: String?
    private var _userId: UUID?

    // MARK: - AuthProvider

    public var currentUserId: UUID {
        _userId ?? UUID(uuidString: "00000000-0000-0000-0000-000000000001")!
    }

    public var authHeaders: [String: String] {
        if let token = _token {
            return ["Authorization": "Bearer \(token)"]
        }
        // 回退到 X-User-Id 兼容模式
        return ["X-User-Id": currentUserId.uuidString]
    }

    /// 是否已登录（有有效 Token）
    public var isAuthenticated: Bool {
        _token != nil
    }

    // MARK: - Init

    public init() {
        // 从 Keychain 恢复 Token
        _token = Self.readKeychain(key: Self.tokenKey)
        if let userIdStr = Self.readKeychain(key: Self.userIdKey) {
            _userId = UUID(uuidString: userIdStr)
        }
    }

    // MARK: - Token Management

    /// 保存登录后的 Token 和 User ID
    public func saveCredentials(token: String, userId: UUID) {
        _token = token
        _userId = userId
        Self.writeKeychain(key: Self.tokenKey, value: token)
        Self.writeKeychain(key: Self.userIdKey, value: userId.uuidString)
    }

    /// 清除登录状态（登出）
    public func clearCredentials() {
        _token = nil
        _userId = nil
        Self.deleteKeychain(key: Self.tokenKey)
        Self.deleteKeychain(key: Self.userIdKey)
    }

    // MARK: - Keychain Helpers

    private static func writeKeychain(key: String, value: String) {
        let data = value.data(using: .utf8)!
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrAccount as String: key,
            kSecValueData as String: data,
            kSecAttrAccessible as String: kSecAttrAccessibleAfterFirstUnlockThisDeviceOnly,
        ]

        // 删除已有条目
        SecItemDelete(query as CFDictionary)
        // 添加新条目
        SecItemAdd(query as CFDictionary, nil)
    }

    private static func readKeychain(key: String) -> String? {
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrAccount as String: key,
            kSecReturnData as String: true,
            kSecMatchLimit as String: kSecMatchLimitOne,
        ]

        var result: AnyObject?
        let status = SecItemCopyMatching(query as CFDictionary, &result)
        guard status == errSecSuccess, let data = result as? Data else {
            return nil
        }
        return String(data: data, encoding: .utf8)
    }

    private static func deleteKeychain(key: String) {
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrAccount as String: key,
        ]
        SecItemDelete(query as CFDictionary)
    }
}
