import XCTest
@testable import AIParenting

final class DecodingTests: XCTestCase {

    private let decoder = TestData.makeDecoder()

    // MARK: - ChildResponse

    func testDecodeChildResponse() throws {
        let json = """
        {
            "id": "11111111-1111-1111-1111-111111111111",
            "user_id": "00000000-0000-0000-0000-000000000001",
            "nickname": "小花",
            "birth_year_month": "2023-06",
            "age_months": 30,
            "stage": "24_36m",
            "focus_themes": ["language", "emotion"],
            "risk_level": "normal",
            "onboarding_completed": true,
            "created_at": "2025-01-01T00:00:00Z",
            "updated_at": "2025-06-01T12:00:00Z"
        }
        """
        let child = try decoder.decode(ChildResponse.self, from: json.data(using: .utf8)!)
        XCTAssertEqual(child.nickname, "小花")
        XCTAssertEqual(child.ageMonths, 30)
        XCTAssertEqual(child.stage, "24_36m")
        XCTAssertEqual(child.focusThemes, ["language", "emotion"])
        XCTAssertTrue(child.onboardingCompleted)
    }

    // MARK: - RecordResponse

    func testDecodeRecordResponse() throws {
        let json = """
        {
            "id": "22222222-2222-2222-2222-222222222222",
            "child_id": "11111111-1111-1111-1111-111111111111",
            "type": "quick_check",
            "tags": ["语言", "进步"],
            "content": "宝宝说了第一个完整句子",
            "voice_url": null,
            "transcript": null,
            "scene": "家中",
            "time_of_day": "上午",
            "theme": "language",
            "source_plan_id": null,
            "source_session_id": null,
            "synced_to_plan": false,
            "created_at": "2025-06-01T10:30:00Z"
        }
        """
        let record = try decoder.decode(RecordResponse.self, from: json.data(using: .utf8)!)
        XCTAssertEqual(record.type, "quick_check")
        XCTAssertEqual(record.tags, ["语言", "进步"])
        XCTAssertEqual(record.scene, "家中")
        XCTAssertFalse(record.syncedToPlan)
    }

    // MARK: - PlanResponse with DayTasks

    func testDecodePlanWithDayTasks() throws {
        let json = """
        {
            "id": "33333333-3333-3333-3333-333333333333",
            "child_id": "11111111-1111-1111-1111-111111111111",
            "version": 1,
            "status": "active",
            "title": "语言发展计划",
            "primary_goal": "促进表达能力",
            "focus_theme": "language",
            "priority_scenes": ["家中", "户外"],
            "stage": "24_36m",
            "risk_level_at_creation": "normal",
            "start_date": "2025-06-01",
            "end_date": "2025-06-07",
            "current_day": 3,
            "completion_rate": 0.43,
            "observation_candidates": null,
            "next_week_context": null,
            "next_week_direction": null,
            "weekend_review_prompt": "回顾本周进展",
            "conservative_note": null,
            "ai_generation_id": null,
            "created_at": "2025-06-01T00:00:00Z",
            "updated_at": "2025-06-03T12:00:00Z",
            "day_tasks": [
                {
                    "id": "44444444-4444-4444-4444-444444444444",
                    "plan_id": "33333333-3333-3333-3333-333333333333",
                    "day_number": 1,
                    "main_exercise_title": "命名游戏",
                    "main_exercise_description": "指认物品并说出名称",
                    "natural_embed_title": "日常对话",
                    "natural_embed_description": "在吃饭时描述食物",
                    "demo_script": "宝宝看，这是红色的苹果",
                    "observation_point": "注意宝宝是否能跟随指认",
                    "completion_status": "executed",
                    "completed_at": "2025-06-01T18:00:00Z"
                }
            ]
        }
        """
        let plan = try decoder.decode(PlanResponse.self, from: json.data(using: .utf8)!)
        XCTAssertEqual(plan.title, "语言发展计划")
        XCTAssertEqual(plan.currentDay, 3)
        XCTAssertEqual(plan.completionRate, 0.43, accuracy: 0.001)
        XCTAssertEqual(plan.dayTasks.count, 1)
        XCTAssertEqual(plan.dayTasks[0].mainExerciseTitle, "命名游戏")
        XCTAssertEqual(plan.dayTasks[0].completionStatus, "executed")
    }

    // MARK: - PlanResponse without DayTasks key

    func testDecodePlanMissingDayTasks() throws {
        let json = """
        {
            "id": "33333333-3333-3333-3333-333333333333",
            "child_id": "11111111-1111-1111-1111-111111111111",
            "version": 1,
            "status": "active",
            "title": "测试计划",
            "primary_goal": "目标",
            "focus_theme": "language",
            "stage": "24_36m",
            "risk_level_at_creation": "normal",
            "start_date": "2025-06-01",
            "end_date": "2025-06-07",
            "current_day": 1,
            "completion_rate": 0.0,
            "created_at": "2025-06-01T00:00:00Z",
            "updated_at": "2025-06-01T00:00:00Z"
        }
        """
        let plan = try decoder.decode(PlanResponse.self, from: json.data(using: .utf8)!)
        XCTAssertEqual(plan.dayTasks.count, 0) // 默认空数组
    }

    // MARK: - AISessionResponse

    func testDecodeAISession() throws {
        let json = """
        {
            "id": "55555555-5555-5555-5555-555555555555",
            "child_id": "11111111-1111-1111-1111-111111111111",
            "session_type": "instant_help",
            "status": "completed",
            "input_scenario": "不愿说话",
            "input_text": "宝宝今天一直不开口",
            "context_snapshot": {"age_months": 30},
            "result": {"advice": "试试用手指游戏引导"},
            "error_info": null,
            "degraded_result": null,
            "model_provider": "mock",
            "model_version": "v1",
            "prompt_template_id": "instant_help_v1",
            "latency_ms": 1500,
            "retry_count": 0,
            "created_at": "2025-06-01T10:00:00Z",
            "completed_at": "2025-06-01T10:00:01.500Z"
        }
        """
        let session = try decoder.decode(AISessionResponse.self, from: json.data(using: .utf8)!)
        XCTAssertEqual(session.sessionType, "instant_help")
        XCTAssertEqual(session.status, "completed")
        XCTAssertEqual(session.latencyMs, 1500)
        XCTAssertNotNil(session.result)
    }

    // MARK: - WeeklyFeedbackResponse

    func testDecodeWeeklyFeedback() throws {
        let json = """
        {
            "id": "66666666-6666-6666-6666-666666666666",
            "plan_id": "33333333-3333-3333-3333-333333333333",
            "child_id": "11111111-1111-1111-1111-111111111111",
            "status": "ready",
            "positive_changes": {"items": ["表达词汇量增加"]},
            "opportunities": {"items": ["可以尝试更多互动游戏"]},
            "summary_text": "本周宝宝在语言方面有明显进步",
            "decision_options": {"options": ["continue", "lower_difficulty", "change_focus"]},
            "selected_decision": null,
            "conservative_path_note": null,
            "record_count_this_week": 5,
            "completion_rate_this_week": 0.71,
            "ai_generation_id": null,
            "error_info": null,
            "created_at": "2025-06-07T10:00:00Z",
            "viewed_at": null,
            "decided_at": null
        }
        """
        let feedback = try decoder.decode(WeeklyFeedbackResponse.self, from: json.data(using: .utf8)!)
        XCTAssertEqual(feedback.status, "ready")
        XCTAssertEqual(feedback.recordCountThisWeek, 5)
        XCTAssertEqual(feedback.completionRateThisWeek, 0.71, accuracy: 0.001)
        XCTAssertNotNil(feedback.summaryText)
    }

    // MARK: - WeeklyFeedback with missing defaults

    func testDecodeWeeklyFeedbackMissingDefaults() throws {
        let json = """
        {
            "id": "66666666-6666-6666-6666-666666666666",
            "plan_id": "33333333-3333-3333-3333-333333333333",
            "child_id": "11111111-1111-1111-1111-111111111111",
            "status": "generating",
            "created_at": "2025-06-07T10:00:00Z"
        }
        """
        let feedback = try decoder.decode(WeeklyFeedbackResponse.self, from: json.data(using: .utf8)!)
        XCTAssertEqual(feedback.recordCountThisWeek, 0) // 默认值
        XCTAssertEqual(feedback.completionRateThisWeek, 0.0) // 默认值
    }

    // MARK: - MessageResponse

    func testDecodeMessage() throws {
        let json = """
        {
            "id": "77777777-7777-7777-7777-777777777777",
            "user_id": "00000000-0000-0000-0000-000000000001",
            "child_id": "11111111-1111-1111-1111-111111111111",
            "type": "risk_alert",
            "title": "发展提醒",
            "body": "建议关注宝宝的语言发展",
            "summary": "语言发展提醒",
            "target_page": "child_detail",
            "target_params": {"child_id": "11111111-1111-1111-1111-111111111111"},
            "requires_preview": true,
            "read_status": "unread",
            "push_status": "delivered",
            "push_sent_at": "2025-06-01T10:00:00Z",
            "push_delivered_at": "2025-06-01T10:00:01Z",
            "clicked_at": null,
            "created_at": "2025-06-01T10:00:00Z"
        }
        """
        let message = try decoder.decode(MessageResponse.self, from: json.data(using: .utf8)!)
        XCTAssertEqual(message.type, "risk_alert")
        XCTAssertEqual(message.readStatus, "unread")
        XCTAssertTrue(message.requiresPreview)
        XCTAssertNotNil(message.pushDeliveredAt)
    }

    // MARK: - MessageResponse with missing requiresPreview

    func testDecodeMessageMissingRequiresPreview() throws {
        let json = """
        {
            "id": "77777777-7777-7777-7777-777777777777",
            "user_id": "00000000-0000-0000-0000-000000000001",
            "type": "system",
            "title": "系统消息",
            "body": "系统消息内容",
            "summary": "系统摘要",
            "read_status": "read",
            "push_status": "pending",
            "created_at": "2025-06-01T10:00:00Z"
        }
        """
        let message = try decoder.decode(MessageResponse.self, from: json.data(using: .utf8)!)
        XCTAssertTrue(message.requiresPreview) // 默认 true
    }

    // MARK: - HomeSummaryResponse

    func testDecodeHomeSummary() throws {
        let json = """
        {
            "child": null,
            "active_plan": null,
            "today_task": null,
            "recent_records": [],
            "unread_count": 0,
            "weekly_feedback_status": null,
            "weekly_feedback_id": null
        }
        """
        let summary = try decoder.decode(HomeSummaryResponse.self, from: json.data(using: .utf8)!)
        XCTAssertNil(summary.child)
        XCTAssertEqual(summary.recentRecords.count, 0)
        XCTAssertEqual(summary.unreadCount, 0)
    }

    func testDecodeHomeSummaryMissingDefaults() throws {
        let json = """
        {
            "weekly_feedback_status": null,
            "weekly_feedback_id": null
        }
        """
        let summary = try decoder.decode(HomeSummaryResponse.self, from: json.data(using: .utf8)!)
        XCTAssertEqual(summary.recentRecords.count, 0) // 默认值
        XCTAssertEqual(summary.unreadCount, 0) // 默认值
    }

    // MARK: - Enum Decoding

    func testDecodeEnums() throws {
        XCTAssertEqual(try decoder.decode(ChildStage.self, from: "\"18_24m\"".data(using: .utf8)!), .months18to24)
        XCTAssertEqual(try decoder.decode(RiskLevel.self, from: "\"consult\"".data(using: .utf8)!), .consult)
        XCTAssertEqual(try decoder.decode(FocusTheme.self, from: "\"self_care\"".data(using: .utf8)!), .selfCare)
        XCTAssertEqual(try decoder.decode(FocusTheme.self, from: "\"sensory_processing\"".data(using: .utf8)!), .sensoryProcessing)
        XCTAssertEqual(try decoder.decode(FocusTheme.self, from: "\"attachment_security\"".data(using: .utf8)!), .attachmentSecurity)
        XCTAssertEqual(try decoder.decode(CompletionStatus.self, from: "\"needs_record\"".data(using: .utf8)!), .needsRecord)
        XCTAssertEqual(try decoder.decode(DecisionValue.self, from: "\"lower_difficulty\"".data(using: .utf8)!), .lowerDifficulty)
        XCTAssertEqual(try decoder.decode(MessageType.self, from: "\"risk_alert\"".data(using: .utf8)!), .riskAlert)
        XCTAssertEqual(try decoder.decode(FeedbackStatus.self, from: "\"generating\"".data(using: .utf8)!), .generating)
        XCTAssertEqual(try decoder.decode(SessionStatus.self, from: "\"degraded\"".data(using: .utf8)!), .degraded)
    }
}
