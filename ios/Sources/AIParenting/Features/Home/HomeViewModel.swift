import Foundation
#if canImport(Observation)
import Observation
#endif

/// 首页 ViewModel
///
/// 调用 /home/summary 获取聚合数据，管理 loading/error/data 三态。
@Observable
public final class HomeViewModel {

    // MARK: - State

    public var summary: HomeSummaryResponse?
    public var isLoading = false
    public var error: APIError?

    // MARK: - Computed

    public var child: ChildResponse? { summary?.child }
    public var activePlan: PlanResponse? { summary?.activePlan }
    public var todayTask: DayTaskResponse? { summary?.todayTask }
    public var recentRecords: [RecordResponse] { summary?.recentRecords ?? [] }
    public var unreadCount: Int { summary?.unreadCount ?? 0 }
    public var weeklyFeedbackStatus: String? { summary?.weeklyFeedbackStatus }
    public var weeklyFeedbackId: UUID? { summary?.weeklyFeedbackId }
    public var hasWeeklyFeedbackReady: Bool { weeklyFeedbackStatus == "ready" }

    // MARK: - Dependencies

    private let apiClient: APIClientProtocol
    private let childId: UUID

    public init(apiClient: APIClientProtocol, childId: UUID) {
        self.apiClient = apiClient
        self.childId = childId
    }

    // MARK: - Actions

    @MainActor
    public func loadSummary() async {
        isLoading = true
        error = nil
        do {
            let result: HomeSummaryResponse = try await apiClient.request(.homeSummary(childId: childId))
            summary = result
        } catch let apiError as APIError {
            error = apiError
        } catch {
            self.error = .networkError(underlying: error)
        }
        isLoading = false
    }

    @MainActor
    public func refresh() async {
        await loadSummary()
    }
}
