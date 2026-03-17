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
/// 使用 JWTAuthProvider 实现完整的登录/注册流程。
/// 根据认证状态和 AppState 决定展示登录、Onboarding 还是 MainTabView。
public struct AIParentingApp: App {

    #if canImport(UIKit)
    @UIApplicationDelegateAdaptor(AppDelegate.self) private var appDelegate
    #endif

    private let jwtAuthProvider: JWTAuthProvider
    private let apiClient: APIClient
    @State private var appState: AppState

    public init() {
        let auth = JWTAuthProvider()
        self.jwtAuthProvider = auth
        let client = APIClient(
            config: .default,
            authProvider: auth
        )
        self.apiClient = client
        self._appState = State(initialValue: AppState(apiClient: client, authProvider: auth))
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

/// 根视图：根据认证状态和 AppState 决定展示内容
///
/// - 未登录：展示登录/注册页面
/// - 未初始化：加载屏
/// - 需要 Onboarding：进入引导流程
/// - 正常：进入 MainTabView
struct RootView: View {

    @Environment(AppState.self) private var appState
    @Environment(APIClient.self) private var apiClient

    var body: some View {
        Group {
            if !appState.isAuthenticated {
                // 未登录 → 登录/注册页面
                LoginView(
                    apiClient: apiClient,
                    authProvider: appState.jwtAuthProvider,
                    onLoginSuccess: {
                        Task { @MainActor in
                            appState.handleLoginSuccess()
                        }
                    }
                )
            } else if !appState.isInitialized {
                // 已登录但未加载 → 启动加载
                VStack(spacing: 16) {
                    ProgressView()
                        .scaleEffect(1.2)
                    Text("正在加载...")
                        .font(.subheadline)
                        .foregroundStyle(.secondary)
                }
                .task {
                    await appState.initialize()
                }
            } else if appState.needsOnboarding {
                OnboardingView()
            } else {
                MainTabView()
            }
        }
    }
}
