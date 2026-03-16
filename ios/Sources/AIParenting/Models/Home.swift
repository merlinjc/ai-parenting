import Foundation

/// 首页聚合响应
public struct HomeSummaryResponse: Codable, Sendable {
    public let child: ChildResponse?
    public let activePlan: PlanResponse?
    public let todayTask: DayTaskResponse?
    public let recentRecords: [RecordResponse]
    public let unreadCount: Int
    public let weeklyFeedbackStatus: String?
    public let weeklyFeedbackId: UUID?

    public init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        child = try container.decodeIfPresent(ChildResponse.self, forKey: .child)
        activePlan = try container.decodeIfPresent(PlanResponse.self, forKey: .activePlan)
        todayTask = try container.decodeIfPresent(DayTaskResponse.self, forKey: .todayTask)
        recentRecords = try container.decodeIfPresent([RecordResponse].self, forKey: .recentRecords) ?? []
        unreadCount = try container.decodeIfPresent(Int.self, forKey: .unreadCount) ?? 0
        weeklyFeedbackStatus = try container.decodeIfPresent(String.self, forKey: .weeklyFeedbackStatus)
        weeklyFeedbackId = try container.decodeIfPresent(UUID.self, forKey: .weeklyFeedbackId)
    }

    private enum CodingKeys: String, CodingKey {
        case child, activePlan, todayTask, recentRecords, unreadCount
        case weeklyFeedbackStatus, weeklyFeedbackId
    }
}
