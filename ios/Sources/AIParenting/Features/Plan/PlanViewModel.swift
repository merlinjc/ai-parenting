import Foundation
#if canImport(Observation)
import Observation
#endif

/// 计划 ViewModel
///
/// 获取活跃计划、计划详情、更新日任务完成状态、创建新计划。
@Observable
public final class PlanViewModel {

    // MARK: - State

    public var plan: PlanResponse?
    public var weeklyFeedbackStatus: String?
    public var isLoading = false
    public var isCreating = false
    public var error: APIError?
    public var updateError: APIError?

    // MARK: - Computed

    public var dayTasks: [DayTaskResponse] { plan?.dayTasks ?? [] }
    public var completionRate: Double { plan?.completionRate ?? 0 }

    public var todayTask: DayTaskResponse? {
        guard let plan else { return nil }
        return plan.dayTasks.first { $0.dayNumber == plan.currentDay }
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
        updateError = nil
        guard let planId = plan?.id else { return }
        let update = DayTaskCompletionUpdate(completionStatus: status.rawValue)
        do {
            let updatedTask: DayTaskResponse = try await apiClient.request(
                .updateDayTaskCompletion(planId: planId, dayNumber: dayNumber, update)
            )
            // 更新本地任务列表中对应的日任务
            if var currentPlan = plan {
                var tasks = currentPlan.dayTasks
                if let index = tasks.firstIndex(where: { $0.dayNumber == dayNumber }) {
                    tasks[index] = updatedTask
                }
                // 重新加载计划以获取更新后的 completion_rate
                await loadPlan(planId: planId)
            }
        } catch let apiError as APIError {
            updateError = apiError
        } catch {
            updateError = .networkError(underlying: error)
        }
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
}
