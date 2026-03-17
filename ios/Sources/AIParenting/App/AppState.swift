import Foundation
import UserNotifications
#if canImport(Observation)
import Observation
#endif

// MARK: - Deep Link Target

/// 跨 Tab 深链导航目标
public enum DeepLinkTarget: Equatable {
    /// 跳转到计划详情
    case planDetail(planId: UUID)
    /// 跳转到创建记录（携带来源信息）
    case recordCreate(sourcePlanId: UUID?, sourceSessionId: UUID?, theme: String?)
    /// 跳转到记录列表
    case recordList
    /// 跳转到消息列表
    case messageList
    /// 跳转到周反馈详情
    case weeklyFeedback(feedbackId: UUID)
    /// 跳转到即时求助（携带 planId 上下文）
    case instantHelp(planId: UUID?)
}

/// 全局应用状态管理
///
/// 管理当前活跃的儿童档案、用户信息、认证状态、引导流程和跨 Tab 深链导航。
@Observable
public final class AppState {

    // MARK: - Auth State

    /// JWT 认证提供者（暴露给 LoginView 和 ProfileView 使用）
    public let jwtAuthProvider: JWTAuthProvider

    /// 是否已完成登录认证
    ///
    /// 使用独立的 stored property 而非委托给 JWTAuthProvider.isAuthenticated，
    /// 因为 JWTAuthProvider 不是 @Observable，其内部状态变更不会触发 SwiftUI 刷新。
    /// 在 handleLoginSuccess() / logout() / init 中手动同步。
    public var isAuthenticated: Bool = false

    // MARK: - State

    /// 当前活跃的儿童 ID
    public var activeChildId: UUID?

    /// 当前活跃的儿童信息
    public var activeChild: ChildResponse?

    /// 用户的所有儿童列表
    public var children: [ChildResponse] = []

    /// 用户档案
    public var userProfile: UserProfileResponse?

    /// 是否需要 Onboarding（无儿童档案）
    public var needsOnboarding: Bool {
        children.isEmpty
    }

    /// 是否已完成初始加载
    public var isInitialized = false

    /// 加载状态
    public var isLoading = false

    /// 错误
    public var error: APIError?

    /// 未读消息数（供 Tab 角标显示）
    public var unreadMessageCount: Int = 0

    // MARK: - Deep Link Navigation

    /// 待处理的跨 Tab 导航目标。设置后由 MainTabView 监听并执行导航。
    public var pendingNavigation: DeepLinkTarget?

    /// 触发跨 Tab 导航
    @MainActor
    public func navigate(to target: DeepLinkTarget) {
        pendingNavigation = target
    }

    /// 消费并清除导航目标（由 MainTabView 在执行导航后调用）
    @MainActor
    public func consumeNavigation() {
        pendingNavigation = nil
    }

    // MARK: - Auth Actions

    /// 登录成功后的处理：更新认证状态并触发重新初始化
    @MainActor
    public func handleLoginSuccess() {
        isAuthenticated = true
        isInitialized = false
        error = nil
        children = []
        activeChildId = nil
        activeChild = nil
        userProfile = nil
    }

    /// 登出：清除认证凭证和所有用户数据
    @MainActor
    public func logout() {
        jwtAuthProvider.clearCredentials()
        isAuthenticated = false
        isInitialized = false
        error = nil
        children = []
        activeChildId = nil
        activeChild = nil
        userProfile = nil
        pendingNavigation = nil
        // 清除持久化的活跃儿童 ID
        UserDefaults.standard.removeObject(forKey: Self.childIdKey)
    }

    // MARK: - Child State Refresh

    /// 刷新当前活跃儿童数据（当收到 risk_alert 等消息时调用）
    @MainActor
    public func refreshActiveChild() async {
        guard let childId = activeChildId else { return }
        do {
            let child: ChildResponse = try await apiClient.request(.getChild(childId))
            activeChild = child
            if let index = children.firstIndex(where: { $0.id == childId }) {
                children[index] = child
            }
        } catch {
            // 刷新活跃儿童数据失败，记录日志但不中断流程
            print("[AppState] refreshActiveChild failed: \(error.localizedDescription)")
        }
    }

    // MARK: - Dependencies

    private let apiClient: APIClientProtocol

    /// 暴露 API Client 引用（供 MainTabView 等创建子 ViewModel 使用）
    public var apiClientRef: APIClientProtocol { apiClient }

    /// 推送通知管理器
    public let pushManager: PushNotificationManager

    @MainActor
    public init(apiClient: APIClientProtocol, authProvider: JWTAuthProvider = JWTAuthProvider()) {
        self.pushManager = PushNotificationManager()
        self.apiClient = apiClient
        self.jwtAuthProvider = authProvider
        // 从 Keychain 恢复的 token 同步到 stored property
        self.isAuthenticated = authProvider.isAuthenticated
    }

    // MARK: - Actions

    /// 初始化：加载用户档案和儿童列表
    @MainActor
    public func initialize() async {
        guard !isInitialized else { return }
        isLoading = true
        error = nil

        do {
            // 加载用户档案（含儿童列表）
            let profile: UserProfileResponse = try await apiClient.request(.getProfile)
            userProfile = profile
            children = profile.children

            // 恢复或选择活跃儿童
            if let savedChildId = loadSavedChildId(), children.contains(where: { $0.id == savedChildId }) {
                activeChildId = savedChildId
                activeChild = children.first(where: { $0.id == savedChildId })
            } else if let first = children.first {
                setActiveChild(first)
            }

            isInitialized = true
        } catch let apiError as APIError {
            // 如果是 401 未授权，说明 token 过期，退回登录页
            if case .unauthorized = apiError {
                jwtAuthProvider.clearCredentials()
                isAuthenticated = false
                isInitialized = true // 不可重试，需要重新登录
            } else if case .networkError = apiError {
                // 网络错误可重试，不标记 isInitialized 以允许用户刷新
                error = apiError
            } else {
                error = apiError
                isInitialized = true
            }
        } catch {
            // 网络错误可重试
            self.error = .networkError(underlying: error)
        }

        isLoading = false

        // 初始化完成且有活跃儿童后请求推送权限
        if activeChildId != nil {
            setupPushNotifications()
        }
    }

    /// 配置推送通知管理器并请求权限
    @MainActor
    private func setupPushNotifications() {
        // 设置通知点击回调 → 驱动深链导航
        pushManager.onNotificationTapped = { [weak self] targetPage, params in
            guard let self else { return }
            let target = self.parseDeepLinkTarget(page: targetPage, params: params)
            if let target {
                Task { @MainActor in
                    self.navigate(to: target)
                }
            }
        }

        // 设置 UNUserNotificationCenter delegate
        UNUserNotificationCenter.current().delegate = pushManager

        // 请求权限
        Task {
            await pushManager.requestPermission()
        }
    }

    /// 解析推送通知中的 target_page → DeepLinkTarget
    private func parseDeepLinkTarget(page: String, params: [String: String]) -> DeepLinkTarget? {
        switch page {
        case "plan_detail":
            if let planIdStr = params["plan_id"], let planId = UUID(uuidString: planIdStr) {
                return .planDetail(planId: planId)
            }
            return nil
        case "record_list":
            return .recordList
        case "message_list":
            return .messageList
        case "weekly_feedback":
            if let feedbackIdStr = params["feedback_id"], let feedbackId = UUID(uuidString: feedbackIdStr) {
                return .weeklyFeedback(feedbackId: feedbackId)
            }
            return nil
        case "instant_help":
            let planId = params["plan_id"].flatMap { UUID(uuidString: $0) }
            return .instantHelp(planId: planId)
        default:
            return nil
        }
    }

    /// 将 device token 上报到后端
    @MainActor
    public func registerDeviceToken() async {
        guard let token = pushManager.deviceToken else { return }
        let request = DeviceRegisterRequest(
            pushToken: token,
            platform: "iOS",
            appVersion: Bundle.main.infoDictionary?["CFBundleShortVersionString"] as? String ?? "1.0.0"
        )
        do {
            try await apiClient.requestVoid(.registerDevice(request))
        } catch {
            // 静默失败，下次启动会重试
        }
    }

    /// 切换当前活跃儿童
    @MainActor
    public func setActiveChild(_ child: ChildResponse) {
        activeChildId = child.id
        activeChild = child
        saveChildId(child.id)
    }

    /// 添加新儿童后刷新列表
    @MainActor
    public func refreshChildren() async {
        do {
            let childrenList: [ChildResponse] = try await apiClient.request(.listChildren)
            children = childrenList

            // 如果当前没有活跃儿童，选择第一个
            if activeChildId == nil, let first = childrenList.first {
                setActiveChild(first)
            } else if let id = activeChildId {
                // 更新活跃儿童的最新数据
                activeChild = childrenList.first(where: { $0.id == id })
            }
        } catch {
            print("[AppState] refreshChildren failed: \(error.localizedDescription)")
        }
    }

    /// 刷新用户档案
    @MainActor
    public func refreshProfile() async {
        do {
            let profile: UserProfileResponse = try await apiClient.request(.getProfile)
            userProfile = profile
            children = profile.children
        } catch {
            print("[AppState] refreshProfile failed: \(error.localizedDescription)")
        }
    }

    // MARK: - Persistence

    private static let childIdKey = "ai_parenting_active_child_id"

    private func saveChildId(_ id: UUID) {
        UserDefaults.standard.set(id.uuidString, forKey: Self.childIdKey)
    }

    private func loadSavedChildId() -> UUID? {
        guard let str = UserDefaults.standard.string(forKey: Self.childIdKey) else { return nil }
        return UUID(uuidString: str)
    }
}
