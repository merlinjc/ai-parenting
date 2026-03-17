import Foundation
#if canImport(Observation)
import Observation
#endif

/// 计划 ViewModel
///
/// 获取活跃计划、计划详情、更新日任务完成状态、创建新计划、
/// 缓存解析后的 observationCandidates、暴露 weeklyFeedbackStatus。
@Observable
public final class PlanViewModel {

    // MARK: - State

    public var plan: PlanResponse?
    public var weeklyFeedbackStatus: String?
    public var isLoading = false
    public var isCreating = false
    public var error: APIError?
    public var updateError: APIError?

    public var isUpdating = false

    /// 历次计划列表
    public var planHistory: [PlanResponse] = []
    public var isLoadingHistory = false

    // MARK: - Computed

    public var dayTasks: [DayTaskResponse] { plan?.dayTasks ?? [] }
    public var completionRate: Double { plan?.completionRate ?? 0 }

    public var todayTask: DayTaskResponse? {
        guard let plan else { return nil }
        return plan.dayTasks.first { $0.dayNumber == plan.currentDay }
    }

    /// 缓存解析后的快速打点候选项
    public var cachedObservationCandidates: [ObservationCandidateItem] {
        plan?.parsedObservationCandidates ?? []
    }

    /// 是否有周反馈就绪（ready/viewed/decided 均显示入口）
    public var hasWeeklyFeedback: Bool {
        guard let status = weeklyFeedbackStatus else { return false }
        return ["ready", "viewed", "decided", "generating"].contains(status)
    }

    /// 周反馈入口按钮文字
    public var weeklyFeedbackButtonText: String {
        switch weeklyFeedbackStatus {
        case "ready": return "查看本周反馈（新）"
        case "viewed": return "查看本周反馈"
        case "decided": return "查看反馈与决策"
        case "generating": return "反馈生成中..."
        default: return "查看本周反馈"
        }
    }

    // MARK: - Dependencies

    private let apiClient: APIClientProtocol
    public let childId: UUID

    public init(apiClient: APIClientProtocol, childId: UUID) {
        self.apiClient = apiClient
        self.childId = childId
    }

    // MARK: - Actions

    @MainActor
    public func loadActivePlan() async {
        isLoading = true
        error = nil
        do {
            let result: PlanWithFeedbackStatus = try await apiClient.request(
                .getActivePlan(childId: childId)
            )
            plan = result.plan
            weeklyFeedbackStatus = result.weeklyFeedbackStatus
        } catch let apiError as APIError {
            if case .notFound = apiError {
                plan = nil
            } else {
                error = apiError
            }
        } catch {
            self.error = .networkError(underlying: error)
        }
        isLoading = false
    }

    @MainActor
    public func loadPlan(planId: UUID) async {
        isLoading = true
        error = nil
        do {
            let result: PlanResponse = try await apiClient.request(.getPlan(planId))
            plan = result
        } catch let apiError as APIError {
            error = apiError
        } catch {
            self.error = .networkError(underlying: error)
        }
        isLoading = false
    }

    @MainActor
    public func updateCompletion(dayNumber: Int, status: CompletionStatus) async {
        guard !isUpdating else { return }
        isUpdating = true
        updateError = nil
        guard let planId = plan?.id else {
            isUpdating = false
            return
        }

        // 乐观更新 UI（立即反馈，无需等待网络）
        if let index = plan?.dayTasks.firstIndex(where: { $0.dayNumber == dayNumber }) {
            plan?.dayTasks[index].completionStatus = status.rawValue
        }

        let update = DayTaskCompletionUpdate(completionStatus: status.rawValue)
        do {
            let _: DayTaskResponse = try await apiClient.request(
                .updateDayTaskCompletion(planId: planId, dayNumber: dayNumber, update)
            )
            // 后台重新加载计划以获取准确的 completion_rate
            await loadPlan(planId: planId)
        } catch let apiError as APIError {
            updateError = apiError
            // 回滚乐观更新：重新加载以恢复服务端状态
            await loadPlan(planId: planId)
        } catch {
            updateError = .networkError(underlying: error)
            await loadPlan(planId: planId)
        }
        isUpdating = false
    }

    @MainActor
    public func createNewPlan() async {
        isCreating = true
        error = nil
        do {
            let result: PlanResponse = try await apiClient.request(.createPlan(childId: childId))
            plan = result
        } catch let apiError as APIError {
            error = apiError
        } catch {
            self.error = .networkError(underlying: error)
        }
        isCreating = false
    }

    /// 加载历次计划列表
    @MainActor
    public func loadPlanHistory() async {
        isLoadingHistory = true
        do {
            let result: PlanListResponse = try await apiClient.request(.listPlans(childId: childId))
            planHistory = result.plans
        } catch {
            // 历次计划加载失败不阻断主流程
        }
        isLoadingHistory = false
    }
}
