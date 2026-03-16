import SwiftUI
import AIParenting

/// DevApp 入口 — 仅用于本地开发调试。
///
/// 透传到 AIParenting library 中的 AIParentingApp，
/// 所有业务逻辑保持在 Swift Package 中。
@main
struct AppEntry: App {
    @UIApplicationDelegateAdaptor(AppDelegate.self) private var delegate

    private let wrapped = AIParentingApp()

    var body: some Scene {
        wrapped.body
    }
}

/// 空 AppDelegate，预留扩展点（推送、深链等）。
final class AppDelegate: NSObject, UIApplicationDelegate {
    func application(
        _ application: UIApplication,
        didFinishLaunchingWithOptions launchOptions: [UIApplication.LaunchOptionsKey: Any]? = nil
    ) -> Bool {
        return true
    }
}
