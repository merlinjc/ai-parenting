import Foundation
@testable import AIParenting

/// Mock API 客户端
///
/// 使用端点匹配模式返回预设响应，支持 ViewModel 单元测试。
final class MockAPIClient: APIClientProtocol, @unchecked Sendable {

    /// 记录的请求端点
    var requestedEndpoints: [Endpoint] = []

    /// 预设的错误
    var errorToThrow: APIError?

    /// 预设响应数据（JSON Data → Decodable 解码）
    private var responseData: [String: Data] = [:]

    /// 配置测试用 JSON Decoder
    private let decoder: JSONDecoder = {
        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase
        decoder.dateDecodingStrategy = .custom { decoder in
            let container = try decoder.singleValueContainer()
            let string = try container.decode(String.self)
            let f1 = ISO8601DateFormatter()
            f1.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
            let f2 = ISO8601DateFormatter()
            f2.formatOptions = [.withInternetDateTime]
            for f in [f1, f2] {
                if let date = f.date(from: string) { return date }
            }
            let df = DateFormatter()
            df.dateFormat = "yyyy-MM-dd"
            df.locale = Locale(identifier: "en_US_POSIX")
            if let date = df.date(from: string) { return date }
            throw DecodingError.dataCorruptedError(in: container, debugDescription: "Cannot decode date: \(string)")
        }
        return decoder
    }()

    private let encoder: JSONEncoder = {
        let encoder = JSONEncoder()
        encoder.keyEncodingStrategy = .convertToSnakeCase
        encoder.dateEncodingStrategy = .iso8601
        return encoder
    }()

    /// 设置预设响应（通过 Codable 编码为 Data 再解码，避免 Any 类型擦除）
    func setResponse<T: Codable & Sendable>(_ response: T, for type: T.Type) {
        let key = String(describing: type)
        do {
            let data = try encoder.encode(response)
            responseData[key] = data
        } catch {
            fatalError("MockAPIClient: Failed to encode response for \(key): \(error)")
        }
    }

    /// 直接设置 JSON Data 作为响应
    func setResponseData(_ data: Data, for typeName: String) {
        responseData[typeName] = data
    }

    func request<T: Decodable & Sendable>(_ endpoint: Endpoint) async throws -> T {
        requestedEndpoints.append(endpoint)

        if let error = errorToThrow {
            throw error
        }

        let key = String(describing: T.self)
        guard let data = responseData[key] else {
            fatalError("MockAPIClient: No response data set for type \(key). Call setResponse(_:for:) first.")
        }

        return try decoder.decode(T.self, from: data)
    }

    func requestVoid(_ endpoint: Endpoint) async throws {
        requestedEndpoints.append(endpoint)
        if let error = errorToThrow {
            throw error
        }
    }

    /// 重置状态
    func reset() {
        requestedEndpoints = []
        responseData = [:]
        errorToThrow = nil
    }
}
