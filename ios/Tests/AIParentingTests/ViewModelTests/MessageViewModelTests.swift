import XCTest
@testable import AIParenting

@MainActor
final class MessageViewModelTests: XCTestCase {

    private var mockClient: MockAPIClient!
    private var viewModel: MessageViewModel!

    override func setUp() {
        super.setUp()
        mockClient = MockAPIClient()
        viewModel = MessageViewModel(apiClient: mockClient)
    }

    func testLoadMessagesSuccess() async {
        let response = TestData.makeMessageListResponse(count: 3, unread: 2)
        mockClient.setResponse(response, for: MessageListResponse.self)

        await viewModel.loadMessages()

        XCTAssertEqual(viewModel.messages.count, 3)
        XCTAssertEqual(viewModel.totalUnread, 2)
        XCTAssertFalse(viewModel.hasMore)
        XCTAssertFalse(viewModel.isLoading)
    }

    func testLoadMessagesError() async {
        mockClient.errorToThrow = .networkError(underlying: NSError(domain: "test", code: -1))

        await viewModel.loadMessages()

        XCTAssertTrue(viewModel.messages.isEmpty)
        XCTAssertNotNil(viewModel.error)
    }

    func testFetchUnreadCount() async {
        let response = TestData.makeUnreadCountResponse(count: 7)
        mockClient.setResponse(response, for: UnreadCountResponse.self)

        await viewModel.fetchUnreadCount()

        XCTAssertEqual(viewModel.totalUnread, 7)
    }

    func testMarkAsRead() async {
        // 先加载消息列表
        let listResponse = TestData.makeMessageListResponse(count: 2, unread: 1)
        mockClient.setResponse(listResponse, for: MessageListResponse.self)
        await viewModel.loadMessages()

        let messageId = viewModel.messages[0].id
        XCTAssertEqual(viewModel.totalUnread, 1)

        // 模拟标已读返回
        let json = """
        {
            "id": "\(messageId.uuidString)",
            "user_id": "\(TestData.userId.uuidString)",
            "type": "plan_reminder",
            "title": "消息 1",
            "body": "消息内容 1",
            "summary": "摘要 1",
            "requires_preview": true,
            "read_status": "read",
            "push_status": "pending",
            "created_at": "2025-06-01T10:00:00Z"
        }
        """
        let updatedMessage = try! TestData.makeDecoder().decode(MessageResponse.self, from: json.data(using: .utf8)!)
        mockClient.setResponse(updatedMessage, for: MessageResponse.self)

        await viewModel.markAsRead(messageId)

        XCTAssertEqual(viewModel.totalUnread, 0)
    }

    func testRefresh() async {
        let response = TestData.makeMessageListResponse()
        mockClient.setResponse(response, for: MessageListResponse.self)

        await viewModel.refresh()

        XCTAssertEqual(mockClient.requestedEndpoints.count, 1)
        XCTAssertFalse(viewModel.messages.isEmpty)
    }
}
