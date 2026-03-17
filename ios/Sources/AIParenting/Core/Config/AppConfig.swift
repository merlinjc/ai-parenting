import Foundation

/// 应用全局配置
///
/// 管理服务器地址、超时设置等。支持 DEBUG 模式切换。
public struct AppConfig: Sendable {

    /// 后端 API 基础 URL
    public let baseURL: URL

    /// 普通请求超时时间（秒）
    public let requestTimeout: TimeInterval

    /// AI 请求超时时间（秒），即时求助等待 AI 生成
    public let aiRequestTimeout: TimeInterval

    /// 周反馈轮询间隔（秒）
    public let pollingInterval: TimeInterval

    /// 默认分页大小
    public let defaultPageSize: Int

    public init(baseURL: URL, requestTimeout: TimeInterval, aiRequestTimeout: TimeInterval, pollingInterval: TimeInterval, defaultPageSize: Int) {
        self.baseURL = baseURL
        self.requestTimeout = requestTimeout
        self.aiRequestTimeout = aiRequestTimeout
        self.pollingInterval = pollingInterval
        self.defaultPageSize = defaultPageSize
    }

    /// 生产环境配置（Release 构建使用）
    /// TODO: 上线前替换为实际生产域名
    public static let production: AppConfig = {
        let url = URL(string: "https://api.aiparenting.example.com")!
        // 编译时安全检查：Release 构建禁止使用 example.com 占位域名
        #if !DEBUG
        // 如果此断言触发，说明上线前未替换生产域名
        assert(!url.host!.contains("example.com"),
               "⚠️ 生产环境 URL 仍为 example.com 占位！请在 AppConfig 中替换为实际域名。")
        #endif
        return AppConfig(
            baseURL: url,
            requestTimeout: 30,
            aiRequestTimeout: 90,
            pollingInterval: 3,
            defaultPageSize: 20
        )
    }()

    /// 开发环境配置（本地调试）
    /// 使用 127.0.0.1 而非 localhost，避免 iOS 模拟器 Sandbox 阻止 DNS 解析
    public static let development = AppConfig(
        baseURL: URL(string: "http://127.0.0.1:8000")!,
        requestTimeout: 30,
        aiRequestTimeout: 60,
        pollingInterval: 2,
        defaultPageSize: 20
    )

    /// 默认配置：DEBUG 构建使用开发环境，Release 构建使用生产环境
    public static let `default`: AppConfig = {
        #if DEBUG
        return .development
        #else
        return .production
        #endif
    }()
}
