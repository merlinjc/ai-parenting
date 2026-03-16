import Foundation

/// 健康检查响应
public struct HealthResponse: Codable, Sendable {
    public let status: String
    public let version: String

    public init(status: String, version: String) {
        self.status = status
        self.version = version
    }
}

/// 文件上传响应
public struct FileUploadResponse: Codable, Sendable {
    public let url: String
    public let filename: String
    public let size: Int

    public init(url: String, filename: String, size: Int) {
        self.url = url
        self.filename = filename
        self.size = size
    }
}
