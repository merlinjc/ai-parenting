import XCTest
@testable import AIParenting

@MainActor
final class RecordViewModelTests: XCTestCase {

    private var mockClient: MockAPIClient!
    private var viewModel: RecordViewModel!

    override func setUp() {
        super.setUp()
        mockClient = MockAPIClient()
        viewModel = RecordViewModel(apiClient: mockClient, childId: TestData.childId)
    }

    func testLoadRecordsSuccess() async {
        let response = TestData.makeRecordListResponse(count: 3, hasMore: true)
        mockClient.setResponse(response, for: RecordListResponse.self)

        await viewModel.loadRecords()

        XCTAssertEqual(viewModel.records.count, 3)
        XCTAssertTrue(viewModel.hasMore)
        XCTAssertEqual(viewModel.totalCount, 3)
        XCTAssertFalse(viewModel.isLoading)
    }

    func testLoadRecordsError() async {
        mockClient.errorToThrow = .networkError(underlying: NSError(domain: "test", code: -1))

        await viewModel.loadRecords()

        XCTAssertTrue(viewModel.records.isEmpty)
        XCTAssertNotNil(viewModel.error)
    }

    func testLoadMore() async {
        // 初始加载
        let page1 = TestData.makeRecordListResponse(count: 3, hasMore: true)
        mockClient.setResponse(page1, for: RecordListResponse.self)
        await viewModel.loadRecords()

        // 加载更多
        let page2 = TestData.makeRecordListResponse(count: 2, hasMore: false)
        mockClient.setResponse(page2, for: RecordListResponse.self)
        await viewModel.loadMore()

        XCTAssertEqual(viewModel.records.count, 5)
        XCTAssertFalse(viewModel.hasMore)
    }

    func testCreateRecordSuccess() async {
        let listResponse = TestData.makeRecordListResponse(count: 0)
        mockClient.setResponse(listResponse, for: RecordListResponse.self)
        await viewModel.loadRecords()

        let newRecord = TestData.makeRecordResponse()
        mockClient.setResponse(newRecord, for: RecordResponse.self)

        let create = RecordCreate(childId: TestData.childId, type: "quick_check", content: "测试")
        let success = await viewModel.createRecord(create)

        XCTAssertTrue(success)
        XCTAssertEqual(viewModel.records.count, 1)
        XCTAssertFalse(viewModel.isCreating)
    }

    func testCreateRecordError() async {
        mockClient.errorToThrow = .validationError(detail: "内容不能为空")

        let create = RecordCreate(childId: TestData.childId, type: "quick_check")
        let success = await viewModel.createRecord(create)

        XCTAssertFalse(success)
        XCTAssertNotNil(viewModel.createError)
    }

    func testFilterRecords() async {
        let response = TestData.makeRecordListResponse(count: 2)
        mockClient.setResponse(response, for: RecordListResponse.self)

        await viewModel.applyFilter("event")

        XCTAssertEqual(viewModel.selectedFilter, "event")
        XCTAssertEqual(mockClient.requestedEndpoints.count, 1)
    }
}
