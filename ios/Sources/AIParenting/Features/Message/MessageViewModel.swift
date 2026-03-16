import Foundation
#if canImport(Observation)
import Observation
#endif

/// 消息 ViewModel
///
/// 消息列表加载、未读计数、更新阅读状态、点击回流上报、推送送达上报。
@Observable
public final class MessageViewModel {

    // MARK: - State

    public var messages: [MessageResponse] = []
    public var hasMore = false
    public var totalUnread = 0
    public var isLoading = false
    public var error: APIError?

    // MARK: - Dependencies

    private let apiClient: APIClientProtocol
    private let pageSize: Int

    public init(apiClient: APIClientProtocol, pageSize: Int = 20) {
        self.apiClient = apiClient
        self.pageSize = pageSize
    }

    // MARK: - Actions

    @MainActor
    public func loadMessages() async {
        isLoading = true
        error = nil
        do {
            let result: MessageListResponse = try await apiClient.request(
                .listMessages(limit: pageSize, before: nil)
            )
            messages = result.messages
            hasMore = result.hasMore
            totalUnread = result.totalUnread
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
        guard let lastMessage = messages.last else { return }

        isLoading = true
        do {
            let result: MessageListResponse = try await apiClient.request(
                .listMessages(limit: pageSize, before: lastMessage.createdAt)
            )
            messages.append(contentsOf: result.messages)
            hasMore = result.hasMore
            totalUnread = result.totalUnread
        } catch let apiError as APIError {
            error = apiError
        } catch {
            self.error = .networkError(underlying: error)
        }
        isLoading = false
    }

    @MainActor
    public func markAsRead(_ messageId: UUID) async {
        let update = MessageUpdateRequest(readStatus: "read")
        do {
            let updated: MessageResponse = try await apiClient.request(
                .updateMessage(messageId, update)
            )
            if let index = messages.firstIndex(where: { $0.id == messageId }) {
                messages[index] = updated
            }
            totalUnread = max(0, totalUnread - 1)
        } catch {
            // 静默处理
        }
    }

    @MainActor
    public func reportClick(_ messageId: UUID) async {
        do {
            let updated: MessageResponse = try await apiClient.request(
                .messageClicked(messageId)
            )
            if let index = messages.firstIndex(where: { $0.id == messageId }) {
                messages[index] = updated
            }
        } catch {
            // 静默处理
        }
    }

    @MainActor
    public func reportDelivery(_ messageId: UUID) async {
        do {
            let _: MessageResponse = try await apiClient.request(
                .messageDelivered(messageId)
            )
        } catch {
            // 静默处理
        }
    }

    @MainActor
    public func fetchUnreadCount() async {
        do {
            let result: UnreadCountResponse = try await apiClient.request(.unreadCount)
            totalUnread = result.unreadCount
        } catch {
            // 静默处理
        }
    }

    @MainActor
    public func refresh() async {
        await loadMessages()
    }
}
