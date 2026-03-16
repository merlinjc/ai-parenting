import Foundation
#if canImport(Observation)
import Observation
#endif

/// 记录 ViewModel
///
/// 列表加载（分页+过滤）、创建记录、管理 items/hasMore/isLoading 状态。
@Observable
public final class RecordViewModel {

    // MARK: - State

    public var records: [RecordResponse] = []
    public var hasMore = false
    public var totalCount = 0
    public var isLoading = false
    public var isCreating = false
    public var error: APIError?
    public var createError: APIError?
    public var selectedFilter: String?

    // MARK: - Dependencies

    private let apiClient: APIClientProtocol
    private let childId: UUID
    private let pageSize: Int

    public init(apiClient: APIClientProtocol, childId: UUID, pageSize: Int = 20) {
        self.apiClient = apiClient
        self.childId = childId
        self.pageSize = pageSize
    }

    // MARK: - Actions

    @MainActor
    public func loadRecords() async {
        isLoading = true
        error = nil
        do {
            let result: RecordListResponse = try await apiClient.request(
                .listRecords(childId: childId, limit: pageSize, before: nil, type: selectedFilter)
            )
            records = result.records
            hasMore = result.hasMore
            totalCount = result.total
        } catch let apiError as APIError {
            error = apiError
        } catch {
            self.error = .networkError(underlying: error)
        }
        isLoading = false
    }

    @MainActor
    public func loadMore() async {
        guard hasMore, !isLoading else { return }
        guard let lastRecord = records.last else { return }

        isLoading = true
        do {
            let result: RecordListResponse = try await apiClient.request(
                .listRecords(childId: childId, limit: pageSize, before: lastRecord.createdAt, type: selectedFilter)
            )
            records.append(contentsOf: result.records)
            hasMore = result.hasMore
        } catch let apiError as APIError {
            error = apiError
        } catch {
            self.error = .networkError(underlying: error)
        }
        isLoading = false
    }

    @MainActor
    public func createRecord(_ create: RecordCreate) async -> Bool {
        isCreating = true
        createError = nil
        do {
            let newRecord: RecordResponse = try await apiClient.request(.createRecord(create))
            records.insert(newRecord, at: 0)
            totalCount += 1
            isCreating = false
            return true
        } catch let apiError as APIError {
            createError = apiError
            isCreating = false
            return false
        } catch {
            createError = .networkError(underlying: error)
            isCreating = false
            return false
        }
    }

    @MainActor
    public func applyFilter(_ type: String?) async {
        selectedFilter = type
        await loadRecords()
    }

    @MainActor
    public func refresh() async {
        await loadRecords()
    }
}
