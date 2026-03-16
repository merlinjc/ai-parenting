import Foundation
#if canImport(Observation)
import Observation
#endif

/// 即时求助 ViewModel
///
/// 调用 /ai/instant-help（60s 超时）、管理请求/结果/错误状态。
@Observable
public final class InstantHelpViewModel {

    // MARK: - State

    public var session: AISessionResponse?
    public var isLoading = false
    public var error: APIError?

    // MARK: - Computed

    public var isCompleted: Bool { session?.status == "completed" }
    public var isFailed: Bool { session?.status == "failed" }
    public var isDegraded: Bool { session?.status == "degraded" }
    public var hasResult: Bool { session?.result != nil || session?.degradedResult != nil }

    // MARK: - Dependencies

    private let apiClient: APIClientProtocol

    public init(apiClient: APIClientProtocol) {
        self.apiClient = apiClient
    }

    // MARK: - Actions

    @MainActor
    public func sendHelp(childId: UUID, scenario: String?, inputText: String?, planId: UUID? = nil) async {
        isLoading = true
        error = nil
        session = nil

        let request = InstantHelpRequest(
            childId: childId,
            scenario: scenario,
            inputText: inputText,
            planId: planId
        )

        do {
            let result: AISessionResponse = try await apiClient.request(.instantHelp(request))
            session = result
        } catch let apiError as APIError {
            error = apiError
        } catch {
            self.error = .networkError(underlying: error)
        }
        isLoading = false
    }

    @MainActor
    public func loadSession(sessionId: UUID) async {
        do {
            let result: AISessionResponse = try await apiClient.request(.getSession(sessionId))
            session = result
        } catch let apiError as APIError {
            error = apiError
        } catch {
            self.error = .networkError(underlying: error)
        }
    }

    public func reset() {
        session = nil
        error = nil
        isLoading = false
    }
}
