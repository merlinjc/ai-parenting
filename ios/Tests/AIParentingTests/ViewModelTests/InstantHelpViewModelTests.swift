import XCTest
@testable import AIParenting

@MainActor
final class InstantHelpViewModelTests: XCTestCase {

    private var mockClient: MockAPIClient!
    private var viewModel: InstantHelpViewModel!

    override func setUp() {
        super.setUp()
        mockClient = MockAPIClient()
        viewModel = InstantHelpViewModel(apiClient: mockClient)
    }

    func testSendHelpSuccess() async {
        let session = TestData.makeAISessionResponse(status: "completed")
        mockClient.setResponse(session, for: AISessionResponse.self)

        await viewModel.sendHelp(childId: TestData.childId, scenario: "不愿说话", inputText: "宝宝今天不肯开口")

        XCTAssertNotNil(viewModel.session)
        XCTAssertTrue(viewModel.isCompleted)
        XCTAssertTrue(viewModel.hasResult)
        XCTAssertFalse(viewModel.isLoading)
        XCTAssertNil(viewModel.error)
    }

    func testSendHelpDegraded() async {
        let session = TestData.makeAISessionResponse(status: "degraded")
        mockClient.setResponse(session, for: AISessionResponse.self)

        await viewModel.sendHelp(childId: TestData.childId, scenario: "情绪失控", inputText: nil)

        XCTAssertTrue(viewModel.isDegraded)
        XCTAssertFalse(viewModel.isCompleted)
    }

    func testSendHelpError() async {
        mockClient.errorToThrow = .timeout

        await viewModel.sendHelp(childId: TestData.childId, scenario: "其他", inputText: "测试")

        XCTAssertNil(viewModel.session)
        XCTAssertNotNil(viewModel.error)
        XCTAssertFalse(viewModel.isLoading)
    }

    func testReset() async {
        let session = TestData.makeAISessionResponse()
        mockClient.setResponse(session, for: AISessionResponse.self)
        await viewModel.sendHelp(childId: TestData.childId, scenario: "test", inputText: nil)

        viewModel.reset()

        XCTAssertNil(viewModel.session)
        XCTAssertNil(viewModel.error)
        XCTAssertFalse(viewModel.isLoading)
    }

    func testLoadSession() async {
        let session = TestData.makeAISessionResponse()
        mockClient.setResponse(session, for: AISessionResponse.self)

        await viewModel.loadSession(sessionId: UUID())

        XCTAssertNotNil(viewModel.session)
    }
}
