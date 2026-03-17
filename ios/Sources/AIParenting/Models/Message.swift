import Foundation

// MARK: - Request Models

/// 更新消息阅读状态请求
public struct MessageUpdateRequest: Codable, Sendable {
    public let readStatus: String

    public init(readStatus: String) {
        self.readStatus = readStatus
    }
}

// MARK: - Response Models

/// 消息响应
public struct MessageResponse: Codable, Sendable, Identifiable {
    public let id: UUID
    public let userId: UUID
    public let childId: UUID?
    public let type: String
    public let title: String
    public let body: String
    public let summary: String
    public let targetPage: String?
    public let targetParams: AnyCodable?
    public let requiresPreview: Bool
    public var readStatus: String
    public let pushStatus: String
    public let pushSentAt: Date?
    public let pushDeliveredAt: Date?
    public let clickedAt: Date?
    public let createdAt: Date

    public init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        id = try container.decode(UUID.self, forKey: .id)
        userId = try container.decode(UUID.self, forKey: .userId)
        childId = try container.decodeIfPresent(UUID.self, forKey: .childId)
        type = try container.decode(String.self, forKey: .type)
        title = try container.decode(String.self, forKey: .title)
        body = try container.decode(String.self, forKey: .body)
        summary = try container.decode(String.self, forKey: .summary)
        targetPage = try container.decodeIfPresent(String.self, forKey: .targetPage)
        targetParams = try container.decodeIfPresent(AnyCodable.self, forKey: .targetParams)
        requiresPreview = try container.decodeIfPresent(Bool.self, forKey: .requiresPreview) ?? true
        readStatus = try container.decode(String.self, forKey: .readStatus)
        pushStatus = try container.decode(String.self, forKey: .pushStatus)
        pushSentAt = try container.decodeIfPresent(Date.self, forKey: .pushSentAt)
        pushDeliveredAt = try container.decodeIfPresent(Date.self, forKey: .pushDeliveredAt)
        clickedAt = try container.decodeIfPresent(Date.self, forKey: .clickedAt)
        createdAt = try container.decode(Date.self, forKey: .createdAt)
    }

    private enum CodingKeys: String, CodingKey {
        case id, userId, childId, type, title, body, summary
        case targetPage, targetParams, requiresPreview, readStatus
        case pushStatus, pushSentAt, pushDeliveredAt, clickedAt, createdAt
    }
}

/// 消息列表响应
public struct MessageListResponse: Codable, Sendable {
    public let messages: [MessageResponse]
    public let hasMore: Bool
    public let totalUnread: Int

    public init(messages: [MessageResponse], hasMore: Bool, totalUnread: Int) {
        self.messages = messages
        self.hasMore = hasMore
        self.totalUnread = totalUnread
    }
}

/// 未读消息计数响应
public struct UnreadCountResponse: Codable, Sendable {
    public let unreadCount: Int

    public init(unreadCount: Int) {
        self.unreadCount = unreadCount
    }
}
