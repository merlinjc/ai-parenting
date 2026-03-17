import Foundation
#if canImport(Observation)
import Observation
#endif

/// API 客户端协议
///
/// 所有网络请求通过此协议抽象，便于测试时注入 Mock 实现。
public protocol APIClientProtocol: Sendable {
    func request<T: Decodable & Sendable>(_ endpoint: Endpoint) async throws -> T
    func requestVoid(_ endpoint: Endpoint) async throws
    func uploadFile(data: Data, filename: String, mimeType: String) async throws -> FileUploadResponse
}

/// 泛型网络客户端
///
/// 处理 JSON 编解码、Header 注入、错误映射、超时配置。
/// 使用 @Observable 以便通过 SwiftUI `@Environment(APIClient.self)` 注入。
/// 可变并发状态（token 刷新）委托给内部的 `TokenRefreshCoordinator` actor。
@Observable
public final class APIClient: APIClientProtocol, @unchecked Sendable {

    private let config: AppConfig
    private let authProvider: any AuthProvider
    private let session: URLSession
    private let aiSession: URLSession

    private let encoder: JSONEncoder = {
        let encoder = JSONEncoder()
        encoder.keyEncodingStrategy = .convertToSnakeCase
        encoder.dateEncodingStrategy = .iso8601
        return encoder
    }()

    // MARK: - Cached Date Formatters (避免每次解码创建新实例)

    private static let iso8601FractionalFormatter: ISO8601DateFormatter = {
        let f = ISO8601DateFormatter()
        f.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        return f
    }()

    private static let iso8601StandardFormatter: ISO8601DateFormatter = {
        let f = ISO8601DateFormatter()
        f.formatOptions = [.withInternetDateTime]
        return f
    }()

    private static let noTZMicrosecondsFormatter: DateFormatter = {
        let f = DateFormatter()
        f.dateFormat = "yyyy-MM-dd'T'HH:mm:ss.SSSSSS"
        f.locale = Locale(identifier: "en_US_POSIX")
        f.timeZone = TimeZone(secondsFromGMT: 0)
        return f
    }()

    private static let noTZMillisecondsFormatter: DateFormatter = {
        let f = DateFormatter()
        f.dateFormat = "yyyy-MM-dd'T'HH:mm:ss.SSS"
        f.locale = Locale(identifier: "en_US_POSIX")
        f.timeZone = TimeZone(secondsFromGMT: 0)
        return f
    }()

    private static let noTZSecondsFormatter: DateFormatter = {
        let f = DateFormatter()
        f.dateFormat = "yyyy-MM-dd'T'HH:mm:ss"
        f.locale = Locale(identifier: "en_US_POSIX")
        f.timeZone = TimeZone(secondsFromGMT: 0)
        return f
    }()

    private static let dateOnlyFormatter: DateFormatter = {
        let f = DateFormatter()
        f.dateFormat = "yyyy-MM-dd"
        f.locale = Locale(identifier: "en_US_POSIX")
        return f
    }()

    private let decoder: JSONDecoder = {
        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase
        decoder.dateDecodingStrategy = .custom { decoder in
            let container = try decoder.singleValueContainer()
            let string = try container.decode(String.self)

            // 尝试多种 ISO 8601 格式（使用缓存的 formatter）
            if let date = APIClient.iso8601FractionalFormatter.date(from: string) {
                return date
            }
            if let date = APIClient.iso8601StandardFormatter.date(from: string) {
                return date
            }

            // 尝试不带时区的 ISO 8601 格式
            if let date = APIClient.noTZMicrosecondsFormatter.date(from: string) {
                return date
            }
            if let date = APIClient.noTZMillisecondsFormatter.date(from: string) {
                return date
            }
            if let date = APIClient.noTZSecondsFormatter.date(from: string) {
                return date
            }

            // 尝试 date-only 格式 (YYYY-MM-DD)
            if let date = APIClient.dateOnlyFormatter.date(from: string) {
                return date
            }

            throw DecodingError.dataCorruptedError(
                in: container,
                debugDescription: "Cannot decode date: \(string)"
            )
        }
        return decoder
    }()

    public init(config: AppConfig = .default, authProvider: any AuthProvider = MockAuthProvider()) {
        self.config = config
        self.authProvider = authProvider

        let normalConfig = URLSessionConfiguration.default
        normalConfig.timeoutIntervalForRequest = config.requestTimeout
        self.session = URLSession(configuration: normalConfig)

        let aiConfig = URLSessionConfiguration.default
        aiConfig.timeoutIntervalForRequest = config.aiRequestTimeout
        self.aiSession = URLSession(configuration: aiConfig)
    }

    // MARK: - APIClientProtocol

    public func request<T: Decodable & Sendable>(_ endpoint: Endpoint) async throws -> T {
        let data = try await performRequest(endpoint)
        do {
            return try decoder.decode(T.self, from: data)
        } catch {
            throw APIError.decodingError(underlying: error)
        }
    }

    public func requestVoid(_ endpoint: Endpoint) async throws {
        _ = try await performRequest(endpoint)
    }

    /// multipart/form-data 文件上传
    public func uploadFile(data: Data, filename: String, mimeType: String) async throws -> FileUploadResponse {
        let endpoint = Endpoint.uploadFile
        var components = URLComponents()
        components.scheme = config.baseURL.scheme
        components.host = config.baseURL.host
        components.port = config.baseURL.port
        components.path = endpoint.path

        guard let url = components.url else {
            throw APIError.unknown
        }

        var request = URLRequest(url: url)
        request.httpMethod = "POST"

        // 注入认证 Header
        for (key, value) in authProvider.authHeaders {
            request.setValue(value, forHTTPHeaderField: key)
        }

        // 构建 multipart/form-data body
        let boundary = "Boundary-\(UUID().uuidString)"
        request.setValue("multipart/form-data; boundary=\(boundary)", forHTTPHeaderField: "Content-Type")
        request.setValue("application/json", forHTTPHeaderField: "Accept")

        var body = Data()
        body.append("--\(boundary)\r\n".data(using: .utf8)!)
        body.append("Content-Disposition: form-data; name=\"file\"; filename=\"\(filename)\"\r\n".data(using: .utf8)!)
        body.append("Content-Type: \(mimeType)\r\n\r\n".data(using: .utf8)!)
        body.append(data)
        body.append("\r\n--\(boundary)--\r\n".data(using: .utf8)!)
        request.httpBody = body

        let responseData: Data
        let response: URLResponse
        do {
            (responseData, response) = try await session.data(for: request)
        } catch let error as URLError where error.code == .timedOut {
            throw APIError.timeout
        } catch {
            throw APIError.networkError(underlying: error)
        }

        guard let httpResponse = response as? HTTPURLResponse else {
            throw APIError.unknown
        }

        guard (200...299).contains(httpResponse.statusCode) else {
            let message = String(data: responseData, encoding: .utf8)
            throw APIError.fromHTTPStatus(httpResponse.statusCode, message: message)
        }

        do {
            return try decoder.decode(FileUploadResponse.self, from: responseData)
        } catch {
            throw APIError.decodingError(underlying: error)
        }
    }

    // MARK: - Private

    /// Token 刷新协调器（actor-isolated，避免 NSLock 跨 await 的线程安全问题）
    private let refreshCoordinator = TokenRefreshCoordinator()

    private func performRequest(_ endpoint: Endpoint) async throws -> Data {
        let data = try await executeRequest(endpoint)
        return data
    }

    private func executeRequest(_ endpoint: Endpoint) async throws -> Data {
        let urlRequest = try buildRequest(endpoint)
        let activeSession = endpoint.usesAITimeout ? aiSession : session

        let data: Data
        let response: URLResponse
        do {
            (data, response) = try await activeSession.data(for: urlRequest)
        } catch let error as URLError where error.code == .timedOut {
            throw APIError.timeout
        } catch {
            throw APIError.networkError(underlying: error)
        }

        guard let httpResponse = response as? HTTPURLResponse else {
            throw APIError.unknown
        }

        let statusCode = httpResponse.statusCode

        // 401 自动刷新 Token（仅对非认证端点）
        if statusCode == 401, !isAuthEndpoint(endpoint) {
            let refreshed = await attemptTokenRefresh()
            if refreshed {
                // 刷新成功后重试原请求
                return try await retryRequest(endpoint)
            }
            throw APIError.unauthorized
        }

        // 接受预期状态码及 200-299 范围
        guard (200...299).contains(statusCode) else {
            let message = String(data: data, encoding: .utf8)
            throw APIError.fromHTTPStatus(statusCode, message: message)
        }

        return data
    }

    /// 尝试刷新 Token（使用 actor 协调并发刷新）
    private func attemptTokenRefresh() async -> Bool {
        await refreshCoordinator.refreshIfNeeded { [self] in
            do {
                let urlRequest = try buildRequest(.refreshToken)
                let (data, response) = try await session.data(for: urlRequest)
                guard let httpResponse = response as? HTTPURLResponse,
                      (200...299).contains(httpResponse.statusCode) else {
                    return false
                }
                let tokenResponse = try decoder.decode(AuthTokenResponse.self, from: data)
                if let jwtProvider = authProvider as? JWTAuthProvider {
                    jwtProvider.saveCredentials(token: tokenResponse.accessToken, userId: tokenResponse.userId)
                }
                return true
            } catch {
                return false
            }
        }
    }

    /// 重试请求（使用刷新后的 Token）
    private func retryRequest(_ endpoint: Endpoint) async throws -> Data {
        let urlRequest = try buildRequest(endpoint)
        let activeSession = endpoint.usesAITimeout ? aiSession : session

        let (data, response) = try await activeSession.data(for: urlRequest)
        guard let httpResponse = response as? HTTPURLResponse,
              (200...299).contains(httpResponse.statusCode) else {
            let message = String(data: data, encoding: .utf8)
            let code = (response as? HTTPURLResponse)?.statusCode ?? 0
            throw APIError.fromHTTPStatus(code, message: message)
        }
        return data
    }

    /// 判断是否为认证端点（避免循环刷新）
    private func isAuthEndpoint(_ endpoint: Endpoint) -> Bool {
        switch endpoint {
        case .login, .register, .refreshToken:
            return true
        default:
            return false
        }
    }

    private func buildRequest(_ endpoint: Endpoint) throws -> URLRequest {
        var components = URLComponents()
        components.scheme = config.baseURL.scheme
        components.host = config.baseURL.host
        components.port = config.baseURL.port
        components.path = endpoint.path
        components.queryItems = endpoint.queryItems

        guard let url = components.url else {
            throw APIError.unknown
        }

        var request = URLRequest(url: url)
        request.httpMethod = endpoint.method

        // 注入认证 Header
        for (key, value) in authProvider.authHeaders {
            request.setValue(value, forHTTPHeaderField: key)
        }

        // 编码请求体
        if let body = endpoint.body {
            request.setValue("application/json", forHTTPHeaderField: "Content-Type")
            request.httpBody = try encoder.encode(AnyEncodable(body))
        }

        request.setValue("application/json", forHTTPHeaderField: "Accept")

        return request
    }
}

// MARK: - Type Erasure Helper

/// 类型擦除 Encodable 包装
private struct AnyEncodable: Encodable {
    private let _encode: (Encoder) throws -> Void

    init(_ value: any Encodable) {
        self._encode = { encoder in
            try value.encode(to: encoder)
        }
    }

    func encode(to encoder: Encoder) throws {
        try _encode(encoder)
    }
}

// MARK: - Token Refresh Coordinator

/// Actor-based token 刷新协调器
///
/// 确保多个并发 401 响应只触发一次 token 刷新。
/// 后续请求等待第一个刷新结果。
private actor TokenRefreshCoordinator {
    private var refreshTask: Task<Bool, Never>?

    func refreshIfNeeded(_ refreshAction: @Sendable @escaping () async -> Bool) async -> Bool {
        // 如果已有正在进行的刷新任务，等待其完成
        if let existingTask = refreshTask {
            return await existingTask.value
        }

        // 创建新的刷新任务
        let task = Task<Bool, Never> {
            await refreshAction()
        }
        refreshTask = task

        let result = await task.value
        refreshTask = nil
        return result
    }
}
