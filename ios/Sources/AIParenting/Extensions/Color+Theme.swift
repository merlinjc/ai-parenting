import SwiftUI

/// Color 扩展 — 应用主题色
///
/// 定义主色调、功能色和背景色。
extension Color {

    // MARK: - Primary

    /// 主色调蓝色
    public static let appPrimary = Color(red: 0.29, green: 0.56, blue: 0.85) // #4A90D9

    /// 辅助蓝色
    public static let appSecondary = Color(red: 0.36, green: 0.63, blue: 0.91) // #5BA0E8

    /// 强调橙色
    public static let appAccent = Color(red: 0.96, green: 0.65, blue: 0.14) // #F5A623

    // MARK: - Functional

    /// 成功绿色
    public static let appSuccess = Color(red: 0.20, green: 0.78, blue: 0.35) // #34C759

    /// 错误红色
    public static let appError = Color(red: 1.0, green: 0.23, blue: 0.19) // #FF3B30

    /// 警告橙色
    public static let appWarning = Color(red: 1.0, green: 0.58, blue: 0.0) // #FF9500

    /// 信息蓝色
    public static let appInfo = Color(red: 0.0, green: 0.48, blue: 1.0) // #007AFF

    // MARK: - Background

    /// 页面背景（自适应暗色模式）
    public static let appBackground = Color(.systemGroupedBackground)

    /// 卡片背景（自适应暗色模式）
    public static let appSurface = Color(.secondarySystemGroupedBackground)

    /// 浅蓝背景
    public static let appLightBlue = Color(red: 0.94, green: 0.96, blue: 1.0) // #F0F4FF

    // MARK: - Text

    /// 主要文本（自适应暗色模式）
    public static let appTextPrimary = Color(.label)

    /// 次要文本（自适应暗色模式）
    public static let appTextSecondary = Color(.secondaryLabel)

    /// 弱化文本（自适应暗色模式）
    public static let appTextTertiary = Color(.tertiaryLabel)
}
