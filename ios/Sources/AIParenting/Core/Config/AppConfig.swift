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

    /// 默认配置
    /// 使用 127.0.0.1 而非 localhost，避免 iOS 模拟器 Sandbox 阻止 DNS 解析
    public static let `default` = AppConfig(
        baseURL: URL(string: "http://127.0.0.1:8000")!,
        requestTimeout: 30,
        aiRequestTimeout: 60,
        pollingInterval: 2,
        defaultPageSize: 20
    )

    #if DEBUG
    /// 开发环境配置
    public static let development = AppConfig(
        baseURL: URL(string: "http://127.0.0.1:8000")!,
        requestTimeout: 30,
        aiRequestTimeout: 60,
        pollingInterval: 2,
        defaultPageSize: 20
    )
    #endif
}
