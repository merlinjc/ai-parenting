import Foundation
import Security

/// JWT 认证提供者
///
/// 通过邮箱+密码登录获取 JWT Token，使用 Keychain 安全存储 Token。
/// 实现 AuthProvider 协议，为 APIClient 提供 Bearer Token Header。
/// 使用 NSLock 保护内部可变状态，确保多线程安全访问。
public final class JWTAuthProvider: AuthProvider, @unchecked Sendable {

    // MARK: - Keychain Keys

    private static let tokenKey = "ai_parenting_jwt_token"
    private static let userIdKey = "ai_parenting_user_id"

    // MARK: - Thread Safety

    /// 保护 _token 和 _userId 的读写锁
    private let lock = NSLock()

    // MARK: - State (受 lock 保护)

    private var _token: String?
    private var _userId: UUID?

    // MARK: - AuthProvider

    public var currentUserId: UUID? {
        lock.lock()
        defer { lock.unlock() }
        return _userId
    }

    public var authHeaders: [String: String] {
        lock.lock()
        defer { lock.unlock() }
        if let token = _token {
            return ["Authorization": "Bearer \(token)"]
        }
        // 无 token 且有 userId 时回退到 X-User-Id 兼容模式（仅开发环境）
        #if DEBUG
        if let userId = _userId {
            return ["X-User-Id": userId.uuidString]
        }
        #endif
        return [:]
    }

    /// 是否已登录（有有效 Token）
    public var isAuthenticated: Bool {
        lock.lock()
        defer { lock.unlock() }
        return _token != nil
    }

    // MARK: - Init

    public init() {
        // 从 Keychain 恢复 Token（init 中无需加锁，单线程访问）
        _token = Self.readKeychain(key: Self.tokenKey)
        if let userIdStr = Self.readKeychain(key: Self.userIdKey) {
            _userId = UUID(uuidString: userIdStr)
        }
    }

    // MARK: - Token Management

    /// 保存登录后的 Token 和 User ID
    public func saveCredentials(token: String, userId: UUID) {
        lock.lock()
        _token = token
        _userId = userId
        lock.unlock()
        Self.writeKeychain(key: Self.tokenKey, value: token)
        Self.writeKeychain(key: Self.userIdKey, value: userId.uuidString)
    }

    /// 清除登录状态（登出）
    public func clearCredentials() {
        lock.lock()
        _token = nil
        _userId = nil
        lock.unlock()
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
