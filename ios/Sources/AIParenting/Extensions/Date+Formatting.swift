import Foundation

/// Date 扩展 — 格式化工具
extension Date {

    /// 相对时间显示（"3 分钟前"、"昨天" 等）
    public var relativeString: String {
        let formatter = RelativeDateTimeFormatter()
        formatter.locale = Locale(identifier: "zh_CN")
        formatter.unitsStyle = .short
        return formatter.localizedString(for: self, relativeTo: Date())
    }

    /// 格式化为 "MM月dd日"
    public var shortDateString: String {
        let formatter = DateFormatter()
        formatter.locale = Locale(identifier: "zh_CN")
        formatter.dateFormat = "MM月dd日"
        return formatter.string(from: self)
    }

    /// 格式化为 "yyyy年MM月dd日"
    public var fullDateString: String {
        let formatter = DateFormatter()
        formatter.locale = Locale(identifier: "zh_CN")
        formatter.dateFormat = "yyyy年MM月dd日"
        return formatter.string(from: self)
    }

    /// 格式化为 "HH:mm"
    public var timeString: String {
        let formatter = DateFormatter()
        formatter.dateFormat = "HH:mm"
        return formatter.string(from: self)
    }

    /// ISO 8601 格式字符串
    public var iso8601String: String {
        let formatter = ISO8601DateFormatter()
        formatter.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        return formatter.string(from: self)
    }

    /// 从 ISO 8601 字符串解析
    public static func fromISO8601(_ string: String) -> Date? {
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
        return nil
    }
}
