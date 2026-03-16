import Foundation
#if canImport(Observation)
import Observation
#endif

/// 周反馈 ViewModel
///
/// 触发生成（202）→ 轮询等待（2s 间隔）→ 展示结果 → 提交决策 → 创建下周计划。
/// 使用 Task cancellation 管理轮询生命周期。
@Observable
public final class FeedbackViewModel {

    // MARK: - State

    public var feedback: WeeklyFeedbackResponse?
    public var isLoading = false
    public var isGenerating = false
    public var isSubmitting = false
    public var isCreatingPlan = false
    public var error: APIError?
    public var newPlanId: UUID?

    // MARK: - Computed

    public var isReady: Bool { feedback?.status == "ready" || feedback?.status == "viewed" }
    public var isDecided: Bool { feedback?.status == "decided" }
    public var isFailed: Bool { feedback?.status == "failed" }
    public var statusText: String {
        switch feedback?.status {
        case "generating": return "正在生成本周反馈..."
        case "ready": return "本周反馈已生成"
        case "viewed": return "本周反馈"
        case "decided": return "已完成决策"
        case "failed": return "生成失败"
        default: return "周反馈"
        }
    }

    /// 解析后的正向变化列表
    public var parsedPositiveChanges: [FeedbackChangeItem] {
        feedback?.parsedPositiveChanges ?? []
    }

    /// 解析后的改进方向列表
    public var parsedOpportunities: [FeedbackChangeItem] {
        feedback?.parsedOpportunities ?? []
    }

    /// 解析后的 AI 生成决策选项
    public var parsedDecisionOptions: [DecisionOptionItem] {
        feedback?.parsedDecisionOptions ?? []
    }

    /// 保守路径说明
    public var conservativePathNote: String? {
        feedback?.conservativePathNote
    }

    /// 是否有结构化反馈内容（用于判断是否展示结构化 UI）
    public var hasStructuredContent: Bool {
        !parsedPositiveChanges.isEmpty || !parsedOpportunities.isEmpty
    }

    // MARK: - Dependencies

    private let apiClient: APIClientProtocol
    private let pollingInterval: TimeInterval
    private var pollingTask: Task<Void, Never>?

    public init(apiClient: APIClientProtocol, pollingInterval: TimeInterval = 2.0) {
        self.apiClient = apiClient
        self.pollingInterval = pollingInterval
    }

    deinit {
        pollingTask?.cancel()
    }

    // MARK: - Actions

    @MainActor
    public func loadFeedback(feedbackId: UUID) async {
        isLoading = true
        error = nil
        do {
            let result: WeeklyFeedbackResponse = try await apiClient.request(.getFeedback(feedbackId))
            feedback = result
            if feedback?.status == "generating" {
                startPolling(feedbackId: feedbackId)
            }
        } catch let apiError as APIError {
            error = apiError
        } catch {
            self.error = .networkError(underlying: error)
        }
        isLoading = false
    }

    @MainActor
    public func triggerGeneration(planId: UUID) async {
        isGenerating = true
        error = nil
        do {
            let result: WeeklyFeedbackResponse = try await apiClient.request(.createFeedback(planId: planId))
            feedback = result
            if let feedbackId = feedback?.id {
                startPolling(feedbackId: feedbackId)
            }
        } catch let apiError as APIError {
            error = apiError
        } catch {
            self.error = .networkError(underlying: error)
        }
        isGenerating = false
    }

    @MainActor
    public func markViewed() async {
        guard let feedbackId = feedback?.id, feedback?.status == "ready" else { return }
        do {
            let result: WeeklyFeedbackResponse = try await apiClient.request(.markFeedbackViewed(feedbackId))
            feedback = result
        } catch {
            // 静默处理，标记已查看不是关键操作
        }
    }

    @MainActor
    public func submitDecision(_ decision: DecisionValue) async {
        guard let feedbackId = feedback?.id else { return }
        isSubmitting = true
        error = nil
        let request = WeeklyFeedbackDecisionRequest(decision: decision.rawValue)
        do {
            let result: WeeklyFeedbackResponse = try await apiClient.request(.submitDecision(feedbackId, request))
            feedback = result
        } catch let apiError as APIError {
            error = apiError
        } catch {
            self.error = .networkError(underlying: error)
        }
        isSubmitting = false
    }

    /// 决策后创建下周计划
    @MainActor
    public func createNewPlanAfterDecision() async -> UUID? {
        guard let childId = feedback?.childId else { return nil }
        isCreatingPlan = true
        defer { isCreatingPlan = false }

        do {
            let plan: PlanResponse = try await apiClient.request(.createPlan(childId: childId))
            newPlanId = plan.id
            return plan.id
        } catch {
            // 计划创建失败不阻断 UI，用户可稍后手动触发
            return nil
        }
    }

    public func stopPolling() {
        pollingTask?.cancel()
        pollingTask = nil
    }

    // MARK: - Polling

    private func startPolling(feedbackId: UUID) {
        pollingTask?.cancel()
        pollingTask = Task { @MainActor [weak self] in
            guard let self else { return }
            while !Task.isCancelled {
                try? await Task.sleep(nanoseconds: UInt64(self.pollingInterval * 1_000_000_000))
                guard !Task.isCancelled else { break }

                do {
                    let updated: WeeklyFeedbackResponse = try await self.apiClient.request(
                        .getFeedback(feedbackId)
                    )
                    self.feedback = updated
                    if updated.status != "generating" {
                        break
                    }
                } catch {
                    break
                }
            }
        }
    }
}
