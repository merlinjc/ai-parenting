import Foundation

/// 统一 API 错误类型
///
/// 封装所有网络请求可能产生的错误，提供用户友好的提示文案。
public enum APIError: Error, LocalizedError, Sendable {

    /// HTTP 错误响应
    case httpError(statusCode: Int, message: String?)

    /// JSON 解码失败
    case decodingError(underlying: Error)

    /// 网络连接错误
    case networkError(underlying: Error)

    /// 未授权（401）
    case unauthorized

    /// 资源不存在（404）
    case notFound

    /// 资源冲突（409）— 例如邮箱已注册
    case conflict

    /// 请求验证失败（422）
    case validationError(detail: String?)

    /// 服务端错误（500+）
    case serverError(String? = nil)

    /// 请求超时
    case timeout

    /// 未知错误
    case unknown

    public var errorDescription: String? {
        switch self {
        case .httpError(let code, let message):
            return message ?? "请求失败（\(code)）"
        case .decodingError:
            return "数据解析失败，请稍后重试"
        case .networkError:
            return "网络连接异常，请检查网络设置"
        case .unauthorized:
            return "登录已过期，请重新登录"
        case .notFound:
            return "请求的资源不存在"
        case .conflict:
            return "资源冲突，请检查后重试"
        case .validationError(let detail):
            return detail ?? "请求参数有误"
        case .serverError(let msg):
            return msg ?? "服务器繁忙，请稍后重试"
        case .timeout:
            return "请求超时，请稍后重试"
        case .unknown:
            return "未知错误，请稍后重试"
        }
    }

    /// 从 HTTP 状态码构造对应错误
    public static func fromHTTPStatus(_ statusCode: Int, message: String? = nil) -> APIError {
        switch statusCode {
        case 401:
            return .unauthorized
        case 404:
            return .notFound
        case 409:
            return .conflict
        case 422:
            return .validationError(detail: message)
        case 500...599:
            return .serverError(message)
        default:
            return .httpError(statusCode: statusCode, message: message)
        }
    }
}
