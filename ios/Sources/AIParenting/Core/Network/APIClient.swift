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
/// 使用 @Observable 以便通过 SwiftUI Environment 注入。
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

    private let decoder: JSONDecoder = {
        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase
        decoder.dateDecodingStrategy = .custom { decoder in
            let container = try decoder.singleValueContainer()
            let string = try container.decode(String.self)

            // 尝试多种 ISO 8601 格式
            let formatters: [ISO8601DateFormatter] = {
                let f1 = ISO8601DateFormatter()
                f1.formatOptions = [.withInternetDateTime, .withFractionalSeconds]

                let f2 = ISO8601DateFormatter()
                f2.formatOptions = [.withInternetDateTime]

                return [f1, f2]
            }()

            for formatter in formatters {
                if let date = formatter.date(from: string) {
                    return date
                }
            }

            // 尝试不带时区的 ISO 8601 格式 (YYYY-MM-DDTHH:mm:ss / YYYY-MM-DDTHH:mm:ss.SSS)
            // 后端可能返回不含 Z 时区后缀的 datetime
            let noTZFormatters: [DateFormatter] = {
                let f1 = DateFormatter()
                f1.dateFormat = "yyyy-MM-dd'T'HH:mm:ss.SSSSSS"
                f1.locale = Locale(identifier: "en_US_POSIX")
                f1.timeZone = TimeZone(secondsFromGMT: 0)

                let f2 = DateFormatter()
                f2.dateFormat = "yyyy-MM-dd'T'HH:mm:ss.SSS"
                f2.locale = Locale(identifier: "en_US_POSIX")
                f2.timeZone = TimeZone(secondsFromGMT: 0)

                let f3 = DateFormatter()
                f3.dateFormat = "yyyy-MM-dd'T'HH:mm:ss"
                f3.locale = Locale(identifier: "en_US_POSIX")
                f3.timeZone = TimeZone(secondsFromGMT: 0)

                return [f1, f2, f3]
            }()

            for formatter in noTZFormatters {
                if let date = formatter.date(from: string) {
                    return date
                }
            }

            // 尝试 date-only 格式 (YYYY-MM-DD)
            let dateOnlyFormatter = DateFormatter()
            dateOnlyFormatter.dateFormat = "yyyy-MM-dd"
            dateOnlyFormatter.locale = Locale(identifier: "en_US_POSIX")
            if let date = dateOnlyFormatter.date(from: string) {
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

    private func performRequest(_ endpoint: Endpoint) async throws -> Data {
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

        // 接受预期状态码及 200-299 范围
        guard (200...299).contains(statusCode) else {
            let message = String(data: data, encoding: .utf8)
            throw APIError.fromHTTPStatus(statusCode, message: message)
        }

        return data
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
