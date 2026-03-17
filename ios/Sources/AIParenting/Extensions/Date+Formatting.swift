import Foundation

/// Date 扩展 — 格式化工具
extension Date {

    // MARK: - Cached Formatters (性能优化，避免每次调用创建新实例)

    private static let relativeDateFormatter: RelativeDateTimeFormatter = {
        let formatter = RelativeDateTimeFormatter()
        formatter.locale = Locale(identifier: "zh_CN")
        formatter.unitsStyle = .short
        return formatter
    }()

    private static let shortDateFormatter: DateFormatter = {
        let formatter = DateFormatter()
        formatter.locale = Locale(identifier: "zh_CN")
        formatter.dateFormat = "MM月dd日"
        return formatter
    }()

    private static let fullDateFormatter: DateFormatter = {
        let formatter = DateFormatter()
        formatter.locale = Locale(identifier: "zh_CN")
        formatter.dateFormat = "yyyy年MM月dd日"
        return formatter
    }()

    private static let timeFormatter: DateFormatter = {
        let formatter = DateFormatter()
        formatter.dateFormat = "HH:mm"
        return formatter
    }()

    private static let iso8601WithFractionalSeconds: ISO8601DateFormatter = {
        let f = ISO8601DateFormatter()
        f.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        return f
    }()

    private static let iso8601Standard: ISO8601DateFormatter = {
        let f = ISO8601DateFormatter()
        f.formatOptions = [.withInternetDateTime]
        return f
    }()

    /// 相对时间显示（"3 分钟前"、"昨天" 等）
    public var relativeString: String {
        Self.relativeDateFormatter.localizedString(for: self, relativeTo: Date())
    }

    /// 格式化为 "MM月dd日"
    public var shortDateString: String {
        Self.shortDateFormatter.string(from: self)
    }

    /// 格式化为 "yyyy年MM月dd日"
    public var fullDateString: String {
        Self.fullDateFormatter.string(from: self)
    }

    /// 格式化为 "HH:mm"
    public var timeString: String {
        Self.timeFormatter.string(from: self)
    }

    /// ISO 8601 格式字符串
    public var iso8601String: String {
        Self.iso8601WithFractionalSeconds.string(from: self)
    }

    /// 从 ISO 8601 字符串解析
    public static func fromISO8601(_ string: String) -> Date? {
        if let date = iso8601WithFractionalSeconds.date(from: string) {
            return date
        }
        if let date = iso8601Standard.date(from: string) {
            return date
        }
        return nil
    }
}
