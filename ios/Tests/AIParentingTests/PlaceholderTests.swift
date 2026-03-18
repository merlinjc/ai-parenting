import XCTest
@testable import AIParenting

final class PlaceholderTests: XCTestCase {

    func testAppConfigDefaults() {
        let config = AppConfig.default
        XCTAssertEqual(config.requestTimeout, 30)
        XCTAssertEqual(config.aiRequestTimeout, 60)
        XCTAssertEqual(config.pollingInterval, 2)
        XCTAssertEqual(config.defaultPageSize, 20)
    }

    func testMockAuthProvider() {
        let auth = MockAuthProvider()
        XCTAssertEqual(auth.currentUserId.uuidString, "00000000-0000-0000-0000-000000000001")
        XCTAssertEqual(auth.authHeaders["X-User-Id"], "00000000-0000-0000-0000-000000000001")
    }

    func testAPIErrorMessages() {
        let error = APIError.unauthorized
        XCTAssertEqual(error.errorDescription, "登录已过期，请重新登录")

        let notFound = APIError.notFound
        XCTAssertEqual(notFound.errorDescription, "请求的资源不存在")

        let fromStatus = APIError.fromHTTPStatus(404)
        XCTAssertEqual(fromStatus.errorDescription, "请求的资源不存在")
    }

    func testEnumRawValues() {
        XCTAssertEqual(ChildStage.months18to24.rawValue, "18_24m")
        XCTAssertEqual(RiskLevel.normal.rawValue, "normal")
        XCTAssertEqual(FocusTheme.selfCare.rawValue, "self_care")
        XCTAssertEqual(FocusTheme.sensoryProcessing.rawValue, "sensory_processing")
        XCTAssertEqual(FocusTheme.attachmentSecurity.rawValue, "attachment_security")
        XCTAssertEqual(CompletionStatus.needsRecord.rawValue, "needs_record")
        XCTAssertEqual(DecisionValue.lowerDifficulty.rawValue, "lower_difficulty")
        XCTAssertEqual(MessageType.riskAlert.rawValue, "risk_alert")
        XCTAssertEqual(FeedbackStatus.generating.rawValue, "generating")
        XCTAssertEqual(RecordType.quickCheck.rawValue, "quick_check")
    }
}
