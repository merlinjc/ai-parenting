import Foundation
#if canImport(Observation)
import Observation
#endif

/// 首页 ViewModel
///
/// 调用 /home/summary 获取聚合数据，启动时刷新月龄，管理 loading/error/data 三态。
@Observable
public final class HomeViewModel {

    // MARK: - State

    public var summary: HomeSummaryResponse?
    public var isLoading = false
    public var error: APIError?

    // MARK: - Task Action State

    /// 今日任务的行动按钮状态
    public enum TaskActionState {
        case start       // 待执行 → "开始今日练习"
        case record      // 已执行未记录 → "去记录"
        case completed   // 已完成 → "查看详情"

        public var title: String {
            switch self {
            case .start: "开始今日练习"
            case .record: "去记录"
            case .completed: "查看详情"
            }
        }

        public var icon: String {
            switch self {
            case .start: "play.circle.fill"
            case .record: "square.and.pencil"
            case .completed: "checkmark.circle.fill"
            }
        }
    }

    // MARK: - Computed

    public var child: ChildResponse? { summary?.child }
    public var activePlan: PlanResponse? { summary?.activePlan }
    public var todayTask: DayTaskResponse? { summary?.todayTask }
    public var recentRecords: [RecordResponse] { summary?.recentRecords ?? [] }
    public var unreadCount: Int { summary?.unreadCount ?? 0 }
    public var weeklyFeedbackStatus: String? { summary?.weeklyFeedbackStatus }
    public var weeklyFeedbackId: UUID? { summary?.weeklyFeedbackId }
    public var greeting: String { summary?.greeting ?? "" }
    public var streakDays: Int { summary?.streakDays ?? 0 }
    public var weekDayStatuses: [String] { summary?.weekDayStatuses ?? [] }

    public var hasWeeklyFeedbackReady: Bool {
        weeklyFeedbackStatus == "ready" || weeklyFeedbackStatus == "viewed"
    }

    /// 今日任务的行动状态
    public var taskActionState: TaskActionState {
        guard let task = todayTask else { return .start }
        switch task.completionStatus {
        case "executed":
            return .completed
        case "needs_record":
            return .record
        default:
            return .start
        }
    }

    /// 计划阶段显示名
    public var stageDisplayName: String? {
        guard let stage = activePlan?.stage else { return nil }
        return ChildStage(rawValue: stage)?.displayName
    }

    /// 风险等级
    public var riskLevel: RiskLevel? {
        guard let level = activePlan?.riskLevelAtCreation ?? child?.riskLevel else { return nil }
        return RiskLevel(rawValue: level)
    }

    /// 是否有待处理的回流项
    public var hasPendingReturnFlow: Bool {
        hasWeeklyFeedbackReady || unreadCount > 0
    }

    /// 回流摘要文本
    public var returnFlowSummary: String {
        var items: [String] = []
        if hasWeeklyFeedbackReady {
            items.append("周反馈已生成")
        }
        if unreadCount > 0 {
            items.append("\(unreadCount) 条未读消息")
        }
        return items.joined(separator: " · ")
    }

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
            // 并行执行月龄刷新和首页摘要请求（减少 200-500ms 串行等待）
            async let refreshTask: Void = {
                _ = try? await apiClient.request(.refreshStage(childId)) as ChildResponse
            }()
            async let summaryTask = apiClient.request(.homeSummary(childId: childId)) as HomeSummaryResponse

            // 等待两个并行任务完成
            _ = await refreshTask
            let result = try await summaryTask
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
