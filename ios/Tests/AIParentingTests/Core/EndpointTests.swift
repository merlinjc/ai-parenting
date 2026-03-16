import XCTest
@testable import AIParenting

final class EndpointTests: XCTestCase {

    private let testId = UUID(uuidString: "11111111-1111-1111-1111-111111111111")!
    private let testChildId = UUID(uuidString: "22222222-2222-2222-2222-222222222222")!

    // MARK: - System

    func testHealthEndpoint() {
        let ep = Endpoint.health
        XCTAssertEqual(ep.method, "GET")
        XCTAssertEqual(ep.path, "/health")
        XCTAssertNil(ep.queryItems)
        XCTAssertNil(ep.body)
    }

    // MARK: - Children

    func testListChildren() {
        let ep = Endpoint.listChildren
        XCTAssertEqual(ep.method, "GET")
        XCTAssertEqual(ep.path, "/api/v1/children")
    }

    func testGetChild() {
        let ep = Endpoint.getChild(testId)
        XCTAssertEqual(ep.method, "GET")
        XCTAssertTrue(ep.path.contains(testId.uuidString))
    }

    func testCreateChild() {
        let create = ChildCreate(nickname: "宝宝", birthYearMonth: "2024-01")
        let ep = Endpoint.createChild(create)
        XCTAssertEqual(ep.method, "POST")
        XCTAssertEqual(ep.path, "/api/v1/children")
        XCTAssertNotNil(ep.body)
        XCTAssertEqual(ep.expectedStatusCode, 201)
    }

    func testUpdateChild() {
        let update = ChildUpdate(nickname: "新名字")
        let ep = Endpoint.updateChild(testId, update)
        XCTAssertEqual(ep.method, "PATCH")
        XCTAssertTrue(ep.path.contains(testId.uuidString))
    }

    func testRefreshStage() {
        let ep = Endpoint.refreshStage(testId)
        XCTAssertEqual(ep.method, "POST")
        XCTAssertTrue(ep.path.hasSuffix("/refresh-stage"))
    }

    func testCompleteOnboarding() {
        let ep = Endpoint.completeOnboarding(testId)
        XCTAssertEqual(ep.method, "POST")
        XCTAssertTrue(ep.path.hasSuffix("/complete-onboarding"))
    }

    // MARK: - Records

    func testListRecords() {
        let ep = Endpoint.listRecords(childId: testChildId, limit: 10, before: nil, type: "event")
        XCTAssertEqual(ep.method, "GET")
        XCTAssertEqual(ep.path, "/api/v1/records")
        let queryItems = ep.queryItems!
        XCTAssertTrue(queryItems.contains { $0.name == "child_id" && $0.value == testChildId.uuidString })
        XCTAssertTrue(queryItems.contains { $0.name == "limit" && $0.value == "10" })
        XCTAssertTrue(queryItems.contains { $0.name == "type" && $0.value == "event" })
    }

    func testCreateRecord() {
        let create = RecordCreate(childId: testChildId, type: "quick_check")
        let ep = Endpoint.createRecord(create)
        XCTAssertEqual(ep.method, "POST")
        XCTAssertEqual(ep.expectedStatusCode, 201)
    }

    // MARK: - Plans

    func testGetActivePlan() {
        let ep = Endpoint.getActivePlan(childId: testChildId)
        XCTAssertEqual(ep.method, "GET")
        XCTAssertEqual(ep.path, "/api/v1/plans/active")
        XCTAssertTrue(ep.queryItems!.contains { $0.name == "child_id" })
    }

    func testCreatePlan() {
        let ep = Endpoint.createPlan(childId: testChildId)
        XCTAssertEqual(ep.method, "POST")
        XCTAssertEqual(ep.path, "/api/v1/plans")
        XCTAssertNotNil(ep.body)
        XCTAssertEqual(ep.expectedStatusCode, 201)
    }

    func testUpdateDayTaskCompletion() {
        let update = DayTaskCompletionUpdate(completionStatus: "executed")
        let ep = Endpoint.updateDayTaskCompletion(planId: testId, dayNumber: 3, update)
        XCTAssertEqual(ep.method, "POST")
        XCTAssertTrue(ep.path.contains("/days/3/completion"))
    }

    // MARK: - AI Sessions

    func testInstantHelp() {
        let request = InstantHelpRequest(childId: testChildId)
        let ep = Endpoint.instantHelp(request)
        XCTAssertEqual(ep.method, "POST")
        XCTAssertEqual(ep.path, "/api/v1/ai/instant-help")
        XCTAssertTrue(ep.usesAITimeout)
        XCTAssertEqual(ep.expectedStatusCode, 201)
    }

    func testGetSession() {
        let ep = Endpoint.getSession(testId)
        XCTAssertEqual(ep.method, "GET")
        XCTAssertTrue(ep.path.contains(testId.uuidString))
        XCTAssertFalse(ep.usesAITimeout)
    }

    // MARK: - Home

    func testHomeSummary() {
        let ep = Endpoint.homeSummary(childId: testChildId)
        XCTAssertEqual(ep.method, "GET")
        XCTAssertEqual(ep.path, "/api/v1/home/summary")
        XCTAssertTrue(ep.queryItems!.contains { $0.name == "child_id" })
    }

    // MARK: - Weekly Feedbacks

    func testCreateFeedback() {
        let ep = Endpoint.createFeedback(planId: testId)
        XCTAssertEqual(ep.method, "POST")
        XCTAssertEqual(ep.path, "/api/v1/weekly-feedbacks")
        XCTAssertEqual(ep.expectedStatusCode, 202)
    }

    func testMarkFeedbackViewed() {
        let ep = Endpoint.markFeedbackViewed(testId)
        XCTAssertEqual(ep.method, "POST")
        XCTAssertTrue(ep.path.hasSuffix("/viewed"))
    }

    func testSubmitDecision() {
        let request = WeeklyFeedbackDecisionRequest(decision: "continue")
        let ep = Endpoint.submitDecision(testId, request)
        XCTAssertEqual(ep.method, "POST")
        XCTAssertTrue(ep.path.hasSuffix("/decision"))
    }

    // MARK: - Messages

    func testListMessages() {
        let ep = Endpoint.listMessages(limit: 10, before: nil)
        XCTAssertEqual(ep.method, "GET")
        XCTAssertEqual(ep.path, "/api/v1/messages")
        XCTAssertTrue(ep.queryItems!.contains { $0.name == "limit" && $0.value == "10" })
    }

    func testUnreadCount() {
        let ep = Endpoint.unreadCount
        XCTAssertEqual(ep.method, "GET")
        XCTAssertEqual(ep.path, "/api/v1/messages/unread-count")
    }

    func testUpdateMessage() {
        let update = MessageUpdateRequest(readStatus: "read")
        let ep = Endpoint.updateMessage(testId, update)
        XCTAssertEqual(ep.method, "PATCH")
    }

    func testMessageClicked() {
        let ep = Endpoint.messageClicked(testId)
        XCTAssertEqual(ep.method, "POST")
        XCTAssertTrue(ep.path.hasSuffix("/clicked"))
    }

    func testMessageDelivered() {
        let ep = Endpoint.messageDelivered(testId)
        XCTAssertEqual(ep.method, "POST")
        XCTAssertTrue(ep.path.hasSuffix("/delivered"))
    }
}
