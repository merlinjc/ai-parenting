import XCTest
@testable import AIParenting

@MainActor
final class PlanViewModelTests: XCTestCase {

    private var mockClient: MockAPIClient!
    private var viewModel: PlanViewModel!

    override func setUp() {
        super.setUp()
        mockClient = MockAPIClient()
        viewModel = PlanViewModel(apiClient: mockClient, childId: TestData.childId)
    }

    func testLoadActivePlanSuccess() async {
        let planWithStatus = TestData.makePlanWithFeedbackStatus(feedbackStatus: "ready")
        mockClient.setResponse(planWithStatus, for: PlanWithFeedbackStatus.self)

        await viewModel.loadActivePlan()

        XCTAssertNotNil(viewModel.plan)
        XCTAssertEqual(viewModel.plan?.title, "语言发展第一周")
        XCTAssertEqual(viewModel.weeklyFeedbackStatus, "ready")
        XCTAssertEqual(viewModel.dayTasks.count, 2)
        XCTAssertFalse(viewModel.isLoading)
        XCTAssertNil(viewModel.error)
    }

    func testLoadActivePlanNotFound() async {
        mockClient.errorToThrow = .notFound

        await viewModel.loadActivePlan()

        XCTAssertNil(viewModel.plan)
        XCTAssertNil(viewModel.error) // 404 不算错误，只是没有活跃计划
        XCTAssertFalse(viewModel.isLoading)
    }

    func testLoadActivePlanError() async {
        mockClient.errorToThrow = .serverError

        await viewModel.loadActivePlan()

        XCTAssertNil(viewModel.plan)
        XCTAssertNotNil(viewModel.error)
        XCTAssertFalse(viewModel.isLoading)
    }

    func testLoadPlanSuccess() async {
        let plan = TestData.makePlanResponse()
        mockClient.setResponse(plan, for: PlanResponse.self)

        await viewModel.loadPlan(planId: TestData.planId)

        XCTAssertNotNil(viewModel.plan)
        XCTAssertEqual(viewModel.plan?.id, TestData.planId)
        XCTAssertEqual(viewModel.completionRate, 0.43)
        XCTAssertFalse(viewModel.isLoading)
    }

    func testCreateNewPlanSuccess() async {
        let plan = TestData.makePlanResponse()
        mockClient.setResponse(plan, for: PlanResponse.self)

        await viewModel.createNewPlan()

        XCTAssertNotNil(viewModel.plan)
        XCTAssertFalse(viewModel.isCreating)
        XCTAssertNil(viewModel.error)
    }

    func testCreateNewPlanError() async {
        mockClient.errorToThrow = .serverError

        await viewModel.createNewPlan()

        XCTAssertNil(viewModel.plan)
        XCTAssertNotNil(viewModel.error)
        XCTAssertFalse(viewModel.isCreating)
    }

    func testTodayTask() async {
        let planWithStatus = TestData.makePlanWithFeedbackStatus()
        mockClient.setResponse(planWithStatus, for: PlanWithFeedbackStatus.self)

        await viewModel.loadActivePlan()

        // currentDay = 3, but tasks only have day 1 and 2, so todayTask should be nil
        XCTAssertNil(viewModel.todayTask)
    }

    func testCompletionRateDefault() {
        // Before loading, completionRate should be 0
        XCTAssertEqual(viewModel.completionRate, 0)
        XCTAssertTrue(viewModel.dayTasks.isEmpty)
    }
}
