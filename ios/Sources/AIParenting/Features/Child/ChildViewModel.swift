import Foundation
#if canImport(Observation)
import Observation
#endif

/// 儿童档案管理 ViewModel
///
/// 支持列表、创建、编辑、删除儿童档案。
@Observable
public final class ChildViewModel {

    // MARK: - State

    public var children: [ChildResponse] = []
    public var isLoading = false
    public var error: APIError?
    public var isSubmitting = false

    // MARK: - Dependencies

    private let apiClient: APIClientProtocol

    public init(apiClient: APIClientProtocol) {
        self.apiClient = apiClient
    }

    // MARK: - Actions

    /// 加载儿童列表
    @MainActor
    public func loadChildren() async {
        isLoading = true
        error = nil
        do {
            let list: [ChildResponse] = try await apiClient.request(.listChildren)
            children = list
        } catch let apiError as APIError {
            error = apiError
        } catch {
            self.error = .networkError(underlying: error)
        }
        isLoading = false
    }

    /// 创建儿童档案
    @MainActor
    public func createChild(_ data: ChildCreate) async -> ChildResponse? {
        isSubmitting = true
        error = nil
        defer { isSubmitting = false }

        do {
            let child: ChildResponse = try await apiClient.request(.createChild(data))
            children.append(child)
            return child
        } catch let apiError as APIError {
            error = apiError
            return nil
        } catch {
            self.error = .networkError(underlying: error)
            return nil
        }
    }

    /// 更新儿童档案
    @MainActor
    public func updateChild(id: UUID, data: ChildUpdate) async -> ChildResponse? {
        isSubmitting = true
        error = nil
        defer { isSubmitting = false }

        do {
            let child: ChildResponse = try await apiClient.request(.updateChild(id, data))
            if let index = children.firstIndex(where: { $0.id == id }) {
                children[index] = child
            }
            return child
        } catch let apiError as APIError {
            error = apiError
            return nil
        } catch {
            self.error = .networkError(underlying: error)
            return nil
        }
    }
}
