import Foundation

/// API 端点枚举
///
/// 27 个 case 与后端全部端点 1:1 映射。
/// 每个 case 提供 method/path/queryItems/body 计算属性。
/// 详细实现在 models-network 任务中完成。
public enum Endpoint: Sendable {

    // MARK: - System
    case health

    // MARK: - Children
    case createChild(ChildCreate)
    case listChildren
    case getChild(UUID)
    case updateChild(UUID, ChildUpdate)
    case refreshStage(UUID)
    case completeOnboarding(UUID)

    // MARK: - Records
    case createRecord(RecordCreate)
    case listRecords(childId: UUID, limit: Int = 20, before: Date? = nil, type: String? = nil)
    case getRecord(UUID)

    // MARK: - Plans
    case getActivePlan(childId: UUID)
    case getPlan(UUID)
    case createPlan(childId: UUID)
    case updateDayTaskCompletion(planId: UUID, dayNumber: Int, DayTaskCompletionUpdate)

    // MARK: - AI Sessions
    case instantHelp(InstantHelpRequest)
    case getSession(UUID)

    // MARK: - Home
    case homeSummary(childId: UUID)

    // MARK: - Weekly Feedbacks
    case createFeedback(planId: UUID)
    case getFeedback(UUID)
    case markFeedbackViewed(UUID)
    case submitDecision(UUID, WeeklyFeedbackDecisionRequest)

    // MARK: - User Profile
    case getProfile
    case updateProfile(UserProfileUpdate)

    // MARK: - Messages
    case listMessages(limit: Int = 20, before: Date? = nil)
    case unreadCount
    case getMessage(UUID)
    case updateMessage(UUID, MessageUpdateRequest)
    case messageClicked(UUID)
    case messageDelivered(UUID)

    // MARK: - Computed Properties

    public var method: String {
        switch self {
        case .health, .listChildren, .getChild, .listRecords, .getRecord,
             .getActivePlan, .getPlan, .homeSummary, .getFeedback,
             .listMessages, .unreadCount, .getMessage, .getSession,
             .getProfile:
            return "GET"
        case .updateChild, .updateMessage, .updateProfile:
            return "PATCH"
        case .createChild, .refreshStage, .completeOnboarding,
             .createRecord, .createPlan, .updateDayTaskCompletion,
             .instantHelp, .createFeedback, .markFeedbackViewed,
             .submitDecision, .messageClicked, .messageDelivered:
            return "POST"
        }
    }

    public var path: String {
        switch self {
        case .health:
            return "/health"

        // Children
        case .createChild:
            return "/api/v1/children"
        case .listChildren:
            return "/api/v1/children"
        case .getChild(let id):
            return "/api/v1/children/\(id.uuidString)"
        case .updateChild(let id, _):
            return "/api/v1/children/\(id.uuidString)"
        case .refreshStage(let id):
            return "/api/v1/children/\(id.uuidString)/refresh-stage"
        case .completeOnboarding(let id):
            return "/api/v1/children/\(id.uuidString)/complete-onboarding"

        // Records
        case .createRecord:
            return "/api/v1/records"
        case .listRecords:
            return "/api/v1/records"
        case .getRecord(let id):
            return "/api/v1/records/\(id.uuidString)"

        // Plans
        case .getActivePlan:
            return "/api/v1/plans/active"
        case .getPlan(let id):
            return "/api/v1/plans/\(id.uuidString)"
        case .createPlan:
            return "/api/v1/plans"
        case .updateDayTaskCompletion(let planId, let day, _):
            return "/api/v1/plans/\(planId.uuidString)/days/\(day)/completion"

        // AI Sessions
        case .instantHelp:
            return "/api/v1/ai/instant-help"
        case .getSession(let id):
            return "/api/v1/ai/sessions/\(id.uuidString)"

        // Home
        case .homeSummary:
            return "/api/v1/home/summary"

        // Weekly Feedbacks
        case .createFeedback:
            return "/api/v1/weekly-feedbacks"
        case .getFeedback(let id):
            return "/api/v1/weekly-feedbacks/\(id.uuidString)"
        case .markFeedbackViewed(let id):
            return "/api/v1/weekly-feedbacks/\(id.uuidString)/viewed"
        case .submitDecision(let id, _):
            return "/api/v1/weekly-feedbacks/\(id.uuidString)/decision"

        // User Profile
        case .getProfile, .updateProfile:
            return "/api/v1/user/profile"

        // Messages
        case .listMessages:
            return "/api/v1/messages"
        case .unreadCount:
            return "/api/v1/messages/unread-count"
        case .getMessage(let id):
            return "/api/v1/messages/\(id.uuidString)"
        case .updateMessage(let id, _):
            return "/api/v1/messages/\(id.uuidString)"
        case .messageClicked(let id):
            return "/api/v1/messages/\(id.uuidString)/clicked"
        case .messageDelivered(let id):
            return "/api/v1/messages/\(id.uuidString)/delivered"
        }
    }

    public var queryItems: [URLQueryItem]? {
        switch self {
        case .listRecords(let childId, let limit, let before, let type):
            var items = [
                URLQueryItem(name: "child_id", value: childId.uuidString),
                URLQueryItem(name: "limit", value: String(limit))
            ]
            if let before {
                items.append(URLQueryItem(name: "before", value: ISO8601DateFormatter().string(from: before)))
            }
            if let type {
                items.append(URLQueryItem(name: "type", value: type))
            }
            return items

        case .getActivePlan(let childId):
            return [URLQueryItem(name: "child_id", value: childId.uuidString)]

        case .homeSummary(let childId):
            return [URLQueryItem(name: "child_id", value: childId.uuidString)]

        case .listMessages(let limit, let before):
            var items = [URLQueryItem(name: "limit", value: String(limit))]
            if let before {
                items.append(URLQueryItem(name: "before", value: ISO8601DateFormatter().string(from: before)))
            }
            return items

        default:
            return nil
        }
    }

    public var body: (any Encodable & Sendable)? {
        switch self {
        case .createChild(let data): return data
        case .updateChild(_, let data): return data
        case .createRecord(let data): return data
        case .createPlan(let childId): return PlanCreateRequest(childId: childId)
        case .updateDayTaskCompletion(_, _, let data): return data
        case .instantHelp(let data): return data
        case .createFeedback(let planId): return WeeklyFeedbackCreateRequest(planId: planId)
        case .submitDecision(_, let data): return data
        case .updateMessage(_, let data): return data
        case .updateProfile(let data): return data
        default: return nil
        }
    }

    /// 是否使用 AI 请求超时（60s）
    public var usesAITimeout: Bool {
        switch self {
        case .instantHelp: return true
        default: return false
        }
    }

    /// 期望的成功状态码
    public var expectedStatusCode: Int {
        switch self {
        case .createChild, .createRecord, .createPlan, .instantHelp:
            return 201
        case .createFeedback:
            return 202
        default:
            return 200
        }
    }
}
