import SwiftUI

/// AI Parenting iOS 客户端 App 定义
///
/// 配置全局依赖注入：APIClient、AuthProvider、AppState。
/// 根据 AppState 决定展示 Onboarding 还是 MainTabView。
/// 当前使用 MockAuthProvider（X-User-Id header），后续替换为 JWT。
///
/// 使用方式：在 Xcode 项目中新建一个 App 入口文件，添加 @main 并创建此 struct。
/// 在纯 Swift Package 中作为 library target，不带 @main 以避免与测试冲突。
public struct AIParentingApp: App {

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
