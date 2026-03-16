import XCTest
@testable import AIParenting

@MainActor
final class FeedbackViewModelTests: XCTestCase {

    private var mockClient: MockAPIClient!
    private var viewModel: FeedbackViewModel!

    override func setUp() {
        super.setUp()
        mockClient = MockAPIClient()
        viewModel = FeedbackViewModel(apiClient: mockClient, pollingInterval: 0.1)
    }

    override func tearDown() {
        viewModel.stopPolling()
        super.tearDown()
    }

    func testLoadFeedbackReady() async {
        let feedback = TestData.makeWeeklyFeedbackResponse(status: "ready")
        mockClient.setResponse(feedback, for: WeeklyFeedbackResponse.self)

        await viewModel.loadFeedback(feedbackId: TestData.feedbackId)

        XCTAssertNotNil(viewModel.feedback)
        XCTAssertTrue(viewModel.isReady)
        XCTAssertFalse(viewModel.isLoading)
    }

    func testLoadFeedbackError() async {
        mockClient.errorToThrow = .notFound

        await viewModel.loadFeedback(feedbackId: TestData.feedbackId)

        XCTAssertNotNil(viewModel.error)
    }

    func testTriggerGeneration() async {
        let feedback = TestData.makeWeeklyFeedbackResponse(status: "generating")
        mockClient.setResponse(feedback, for: WeeklyFeedbackResponse.self)

        await viewModel.triggerGeneration(planId: TestData.planId)

        XCTAssertNotNil(viewModel.feedback)
        XCTAssertEqual(viewModel.feedback?.status, "generating")
        // 轮询已启动
        viewModel.stopPolling()
    }

    func testSubmitDecision() async {
        // 先加载
        let readyFeedback = TestData.makeWeeklyFeedbackResponse(status: "ready")
        mockClient.setResponse(readyFeedback, for: WeeklyFeedbackResponse.self)
        await viewModel.loadFeedback(feedbackId: TestData.feedbackId)

        // 提交决策
        let decidedFeedback = TestData.makeWeeklyFeedbackResponse(status: "decided")
        mockClient.setResponse(decidedFeedback, for: WeeklyFeedbackResponse.self)

        await viewModel.submitDecision(.continue)

        XCTAssertTrue(viewModel.isDecided)
        XCTAssertFalse(viewModel.isSubmitting)
    }

    func testSubmitDecisionError() async {
        let feedback = TestData.makeWeeklyFeedbackResponse(status: "ready")
        mockClient.setResponse(feedback, for: WeeklyFeedbackResponse.self)
        await viewModel.loadFeedback(feedbackId: TestData.feedbackId)

        mockClient.errorToThrow = .serverError

        await viewModel.submitDecision(.lowerDifficulty)

        XCTAssertNotNil(viewModel.error)
        XCTAssertFalse(viewModel.isSubmitting)
    }

    func testFailedStatus() async {
        let feedback = TestData.makeWeeklyFeedbackResponse(status: "failed")
        mockClient.setResponse(feedback, for: WeeklyFeedbackResponse.self)

        await viewModel.loadFeedback(feedbackId: TestData.feedbackId)

        XCTAssertTrue(viewModel.isFailed)
        XCTAssertFalse(viewModel.isReady)
    }

    func testStatusText() async {
        let feedback = TestData.makeWeeklyFeedbackResponse(status: "ready")
        mockClient.setResponse(feedback, for: WeeklyFeedbackResponse.self)
        await viewModel.loadFeedback(feedbackId: TestData.feedbackId)

        XCTAssertEqual(viewModel.statusText, "本周反馈已生成")
    }
}
