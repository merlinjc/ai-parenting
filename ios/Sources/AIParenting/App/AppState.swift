import Foundation
#if canImport(Observation)
import Observation
#endif

/// 全局应用状态管理
///
/// 管理当前活跃的儿童档案、用户信息和引导流程状态。
/// 替代 MainTabView 中的硬编码 childId，支持多孩切换。
@Observable
public final class AppState {

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

    // MARK: - Dependencies

    private let apiClient: APIClientProtocol

    public init(apiClient: APIClientProtocol) {
        self.apiClient = apiClient
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
            error = apiError
            // 即使加载失败也标记已初始化，避免卡在加载状态
            isInitialized = true
        } catch {
            self.error = .networkError(underlying: error)
            isInitialized = true
        }

        isLoading = false
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
            // 静默失败，保持现有数据
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
            // 静默失败
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
