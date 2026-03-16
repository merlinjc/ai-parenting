import Foundation
@testable import AIParenting

/// 测试数据工厂
enum TestData {

    static let childId = UUID(uuidString: "22222222-2222-2222-2222-222222222222")!
    static let planId = UUID(uuidString: "33333333-3333-3333-3333-333333333333")!
    static let feedbackId = UUID(uuidString: "44444444-4444-4444-4444-444444444444")!
    static let userId = UUID(uuidString: "00000000-0000-0000-0000-000000000001")!
    static let now = Date()

    static func makeHomeSummary(unreadCount: Int = 2) -> HomeSummaryResponse {
        let json = """
        {
            "child": {
                "id": "\(childId.uuidString)",
                "user_id": "\(userId.uuidString)",
                "nickname": "小明",
                "birth_year_month": "2024-01",
                "age_months": 26,
                "stage": "24_36m",
                "focus_themes": ["language", "social"],
                "risk_level": "normal",
                "onboarding_completed": true,
                "created_at": "2025-01-01T00:00:00Z",
                "updated_at": "2025-06-01T00:00:00Z"
            },
            "active_plan": null,
            "today_task": null,
            "recent_records": [],
            "unread_count": \(unreadCount),
            "weekly_feedback_status": null,
            "weekly_feedback_id": null
        }
        """
        return try! makeDecoder().decode(HomeSummaryResponse.self, from: json.data(using: .utf8)!)
    }

    static func makeRecordListResponse(count: Int = 3, hasMore: Bool = false) -> RecordListResponse {
        var records: [[String: Any]] = []
        for i in 0..<count {
            records.append([
                "id": UUID().uuidString,
                "child_id": childId.uuidString,
                "type": "quick_check",
                "tags": ["语言"],
                "content": "记录 \(i + 1)",
                "synced_to_plan": false,
                "created_at": "2025-06-0\(min(i + 1, 9))T10:00:00Z"
            ])
        }

        let json: [String: Any] = [
            "records": records,
            "has_more": hasMore,
            "total": count
        ]
        let data = try! JSONSerialization.data(withJSONObject: json)
        return try! makeDecoder().decode(RecordListResponse.self, from: data)
    }

    static func makeRecordResponse() -> RecordResponse {
        let json = """
        {
            "id": "\(UUID().uuidString)",
            "child_id": "\(childId.uuidString)",
            "type": "quick_check",
            "tags": ["语言"],
            "content": "新记录",
            "synced_to_plan": false,
            "created_at": "2025-06-01T10:00:00Z"
        }
        """
        return try! makeDecoder().decode(RecordResponse.self, from: json.data(using: .utf8)!)
    }

    static func makeAISessionResponse(status: String = "completed") -> AISessionResponse {
        let json = """
        {
            "id": "\(UUID().uuidString)",
            "child_id": "\(childId.uuidString)",
            "session_type": "instant_help",
            "status": "\(status)",
            "result": {"advice": "建议文本"},
            "retry_count": 0,
            "created_at": "2025-06-01T10:00:00Z"
        }
        """
        return try! makeDecoder().decode(AISessionResponse.self, from: json.data(using: .utf8)!)
    }

    static func makeWeeklyFeedbackResponse(status: String = "ready") -> WeeklyFeedbackResponse {
        let json = """
        {
            "id": "\(feedbackId.uuidString)",
            "plan_id": "\(planId.uuidString)",
            "child_id": "\(childId.uuidString)",
            "status": "\(status)",
            "summary_text": "本周进步明显",
            "record_count_this_week": 5,
            "completion_rate_this_week": 0.71,
            "created_at": "2025-06-07T10:00:00Z"
        }
        """
        return try! makeDecoder().decode(WeeklyFeedbackResponse.self, from: json.data(using: .utf8)!)
    }

    static func makeMessageListResponse(count: Int = 3, unread: Int = 1) -> MessageListResponse {
        var messages: [[String: Any]] = []
        for i in 0..<count {
            messages.append([
                "id": UUID().uuidString,
                "user_id": userId.uuidString,
                "type": i == 0 ? "plan_reminder" : "system",
                "title": "消息 \(i + 1)",
                "body": "消息内容 \(i + 1)",
                "summary": "摘要 \(i + 1)",
                "requires_preview": true,
                "read_status": i < unread ? "unread" : "read",
                "push_status": "pending",
                "created_at": "2025-06-0\(min(i + 1, 9))T10:00:00Z"
            ])
        }

        let json: [String: Any] = [
            "messages": messages,
            "has_more": false,
            "total_unread": unread
        ]
        let data = try! JSONSerialization.data(withJSONObject: json)
        return try! makeDecoder().decode(MessageListResponse.self, from: data)
    }

    static func makePlanResponse(completionRate: Double = 0.43) -> PlanResponse {
        let taskId1 = UUID().uuidString
        let taskId2 = UUID().uuidString
        let json = """
        {
            "id": "\(planId.uuidString)",
            "child_id": "\(childId.uuidString)",
            "version": 1,
            "status": "active",
            "title": "语言发展第一周",
            "primary_goal": "增加主动表达",
            "focus_theme": "language",
            "stage": "24_36m",
            "risk_level_at_creation": "normal",
            "start_date": "2025-06-01",
            "end_date": "2025-06-07",
            "current_day": 3,
            "completion_rate": \(completionRate),
            "created_at": "2025-06-01T00:00:00Z",
            "updated_at": "2025-06-03T00:00:00Z",
            "day_tasks": [
                {
                    "id": "\(taskId1)",
                    "plan_id": "\(planId.uuidString)",
                    "day_number": 1,
                    "main_exercise_title": "看图说话",
                    "main_exercise_description": "用绘本引导孩子描述画面",
                    "natural_embed_title": "餐桌对话",
                    "natural_embed_description": "吃饭时引导孩子表达喜好",
                    "demo_script": "宝宝你看，这是什么呀？",
                    "observation_point": "是否主动命名物品",
                    "completion_status": "done",
                    "completed_at": "2025-06-01T18:00:00Z"
                },
                {
                    "id": "\(taskId2)",
                    "plan_id": "\(planId.uuidString)",
                    "day_number": 2,
                    "main_exercise_title": "角色扮演",
                    "main_exercise_description": "用玩偶进行简单对话游戏",
                    "natural_embed_title": "散步聊天",
                    "natural_embed_description": "散步时描述所见事物",
                    "demo_script": "小熊说：你好呀！",
                    "observation_point": "能否模仿简单对话",
                    "completion_status": "pending",
                    "completed_at": null
                }
            ]
        }
        """
        return try! makeDecoder().decode(PlanResponse.self, from: json.data(using: .utf8)!)
    }

    static func makePlanWithFeedbackStatus(feedbackStatus: String? = nil) -> PlanWithFeedbackStatus {
        let statusValue = feedbackStatus.map { "\"\($0)\"" } ?? "null"
        let taskId1 = UUID().uuidString
        let taskId2 = UUID().uuidString
        let json = """
        {
            "plan": {
                "id": "\(planId.uuidString)",
                "child_id": "\(childId.uuidString)",
                "version": 1,
                "status": "active",
                "title": "语言发展第一周",
                "primary_goal": "增加主动表达",
                "focus_theme": "language",
                "stage": "24_36m",
                "risk_level_at_creation": "normal",
                "start_date": "2025-06-01",
                "end_date": "2025-06-07",
                "current_day": 3,
                "completion_rate": 0.43,
                "created_at": "2025-06-01T00:00:00Z",
                "updated_at": "2025-06-03T00:00:00Z",
                "day_tasks": [
                    {
                        "id": "\(taskId1)",
                        "plan_id": "\(planId.uuidString)",
                        "day_number": 1,
                        "main_exercise_title": "看图说话",
                        "main_exercise_description": "用绘本引导",
                        "natural_embed_title": "餐桌对话",
                        "natural_embed_description": "引导表达",
                        "demo_script": "你看这是什么？",
                        "observation_point": "主动命名",
                        "completion_status": "done",
                        "completed_at": "2025-06-01T18:00:00Z"
                    },
                    {
                        "id": "\(taskId2)",
                        "plan_id": "\(planId.uuidString)",
                        "day_number": 2,
                        "main_exercise_title": "角色扮演",
                        "main_exercise_description": "对话游戏",
                        "natural_embed_title": "散步聊天",
                        "natural_embed_description": "描述事物",
                        "demo_script": "小熊说你好",
                        "observation_point": "模仿对话",
                        "completion_status": "pending",
                        "completed_at": null
                    }
                ]
            },
            "weekly_feedback_status": \(statusValue)
        }
        """
        return try! makeDecoder().decode(PlanWithFeedbackStatus.self, from: json.data(using: .utf8)!)
    }

    static func makeDayTaskResponse(dayNumber: Int = 1, status: String = "done") -> DayTaskResponse {
        let json = """
        {
            "id": "\(UUID().uuidString)",
            "plan_id": "\(planId.uuidString)",
            "day_number": \(dayNumber),
            "main_exercise_title": "看图说话",
            "main_exercise_description": "用绘本引导",
            "natural_embed_title": "餐桌对话",
            "natural_embed_description": "引导表达",
            "demo_script": "你看这是什么？",
            "observation_point": "主动命名",
            "completion_status": "\(status)",
            "completed_at": \(status == "done" ? "\"2025-06-01T18:00:00Z\"" : "null")
        }
        """
        return try! makeDecoder().decode(DayTaskResponse.self, from: json.data(using: .utf8)!)
    }

    static func makeUnreadCountResponse(count: Int = 5) -> UnreadCountResponse {
        return UnreadCountResponse(unreadCount: count)
    }

    // MARK: - Decoder

    static func makeDecoder() -> JSONDecoder {
        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase
        decoder.dateDecodingStrategy = .custom { decoder in
            let container = try decoder.singleValueContainer()
            let string = try container.decode(String.self)
            let f1 = ISO8601DateFormatter()
            f1.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
            let f2 = ISO8601DateFormatter()
            f2.formatOptions = [.withInternetDateTime]
            for f in [f1, f2] {
                if let date = f.date(from: string) { return date }
            }
            let df = DateFormatter()
            df.dateFormat = "yyyy-MM-dd"
            df.locale = Locale(identifier: "en_US_POSIX")
            if let date = df.date(from: string) { return date }
            throw DecodingError.dataCorruptedError(in: container, debugDescription: "Cannot decode date: \(string)")
        }
        return decoder
    }
}
