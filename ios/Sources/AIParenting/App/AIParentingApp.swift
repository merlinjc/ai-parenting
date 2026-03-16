import SwiftUI
#if canImport(UIKit)
import UIKit
#endif

/// APNs 推送 delegate 适配器
///
/// 处理 device token 注册成功/失败回调，将 token 传递给 PushNotificationManager。
#if canImport(UIKit)
public class AppDelegate: NSObject, UIApplicationDelegate {

    /// 由 AIParentingApp 在初始化时注入
    weak var appState: AppState?

    public func application(
        _ application: UIApplication,
        didRegisterForRemoteNotificationsWithDeviceToken deviceToken: Data
    ) {
        appState?.pushManager.handleDeviceToken(deviceToken)
        // 上报 token 到后端
        Task { @MainActor in
            await appState?.registerDeviceToken()
        }
    }

    public func application(
        _ application: UIApplication,
        didFailToRegisterForRemoteNotificationsWithError error: Error
    ) {
        appState?.pushManager.handleRegistrationError(error)
    }
}
#endif

/// AI Parenting iOS 客户端 App 定义
///
/// 配置全局依赖注入：APIClient、AuthProvider、AppState。
/// 根据 AppState 决定展示 Onboarding 还是 MainTabView。
/// 当前使用 MockAuthProvider（X-User-Id header），后续替换为 JWT。
///
/// 使用方式：在 Xcode 项目中新建一个 App 入口文件，添加 @main 并创建此 struct。
/// 在纯 Swift Package 中作为 library target，不带 @main 以避免与测试冲突。
public struct AIParentingApp: App {

    #if canImport(UIKit)
    @UIApplicationDelegateAdaptor(AppDelegate.self) private var appDelegate
    #endif

    private let authProvider: any AuthProvider
    private let apiClient: APIClient
    @State private var appState: AppState

    public init() {
        let auth = MockAuthProvider()
        self.authProvider = auth
        let client = APIClient(
            config: .default,
            authProvider: auth
        )
        self.apiClient = client
        self._appState = State(initialValue: AppState(apiClient: client))
    }

    public var body: some Scene {
        WindowGroup {
            RootView()
                .environment(apiClient)
                .environment(appState)
                .onAppear {
                    #if canImport(UIKit)
                    appDelegate.appState = appState
                    #endif
                }
        }
    }
}

/// 根视图：根据 AppState 决定展示内容
///
/// - 未初始化：加载屏
/// - 需要 Onboarding：进入引导流程
/// - 正常：进入 MainTabView
struct RootView: View {

    @Environment(AppState.self) private var appState

    var body: some View {
        Group {
            if !appState.isInitialized {
                // 启动加载
                VStack(spacing: 16) {
                    ProgressView()
                        .scaleEffect(1.2)
                    Text("正在加载...")
                        .font(.subheadline)
                        .foregroundStyle(.secondary)
                }
            } else if appState.needsOnboarding {
                OnboardingView()
            } else {
                MainTabView()
            }
        }
        .task {
            await appState.initialize()
        }
    }
}
