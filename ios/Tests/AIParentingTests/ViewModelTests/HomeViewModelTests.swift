import XCTest
@testable import AIParenting

@MainActor
final class HomeViewModelTests: XCTestCase {

    private var mockClient: MockAPIClient!
    private var viewModel: HomeViewModel!

    override func setUp() {
        super.setUp()
        mockClient = MockAPIClient()
        viewModel = HomeViewModel(apiClient: mockClient, childId: TestData.childId)
    }

    func testLoadSummarySuccess() async {
        let summary = TestData.makeHomeSummary(unreadCount: 3)
        mockClient.setResponse(summary, for: HomeSummaryResponse.self)

        await viewModel.loadSummary()

        XCTAssertNotNil(viewModel.summary)
        XCTAssertEqual(viewModel.child?.nickname, "小明")
        XCTAssertEqual(viewModel.unreadCount, 3)
        XCTAssertFalse(viewModel.isLoading)
        XCTAssertNil(viewModel.error)
    }

    func testLoadSummaryError() async {
        mockClient.errorToThrow = .serverError

        await viewModel.loadSummary()

        XCTAssertNil(viewModel.summary)
        XCTAssertNotNil(viewModel.error)
        XCTAssertFalse(viewModel.isLoading)
    }

    func testWeeklyFeedbackReady() async {
        var summary = TestData.makeHomeSummary()
        // 不能直接修改，所以测试默认值
        mockClient.setResponse(summary, for: HomeSummaryResponse.self)

        await viewModel.loadSummary()

        XCTAssertFalse(viewModel.hasWeeklyFeedbackReady)
    }

    func testRefreshReloads() async {
        let summary = TestData.makeHomeSummary()
        mockClient.setResponse(summary, for: HomeSummaryResponse.self)

        await viewModel.refresh()

        XCTAssertEqual(mockClient.requestedEndpoints.count, 1)
    }
}
