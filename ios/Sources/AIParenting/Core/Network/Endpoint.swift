import Foundation

/// API 端点枚举
///
/// 27 个 case 与后端全部端点 1:1 映射。
/// 每个 case 提供 method/path/queryItems/body 计算属性。
/// 详细实现在 models-network 任务中完成。
public enum Endpoint: Sendable {

    // MARK: - System
    case health

    // MARK: - Auth
    case register(AuthRegisterRequest)
    case login(AuthLoginRequest)
    case refreshToken

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
    case listPlans(childId: UUID, limit: Int = 20, offset: Int = 0)
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

    // MARK: - Devices
    case registerDevice(DeviceRegisterRequest)

    // MARK: - Plans (Focus Note)
    case appendFocusNote(planId: UUID, PlanFocusNoteUpdate)

    // MARK: - Files
    case uploadFile

    // MARK: - Consult Prep
    case getConsultPrep(childId: UUID)

    // MARK: - Channels
    case listChannelBindings
    case bindChannel(ChannelBindingCreate)
    case unbindChannel(UUID)
    case getChannelPreferences
    case updateChannelPreferences(ChannelPreferenceUpdate)
    case wechatQRCode

    // MARK: - Voice
    case voiceConverse(VoiceConverseRequest)
    case voiceTranscribe(VoiceTranscribeRequest)
    case voiceSynthesize(VoiceSynthesizeRequest)

    // MARK: - Skills
    case listSkills
    case runSleepAnalysis(SleepAnalysisRequest)

    // MARK: - Memory
    case initializeMemory(MemoryInitRequest)

    // MARK: - Computed Properties

    public var method: String {
        switch self {
        case .health, .listChildren, .getChild, .listRecords, .getRecord,
             .getActivePlan, .getPlan, .listPlans, .homeSummary, .getFeedback,
             .listMessages, .unreadCount, .getMessage, .getSession,
             .getProfile, .getConsultPrep,
             .listChannelBindings, .getChannelPreferences, .wechatQRCode,
             .listSkills:
            return "GET"
        case .updateChild, .updateMessage, .updateProfile, .appendFocusNote,
             .updateChannelPreferences:
            return "PATCH"
        case .register, .login, .refreshToken,
             .createChild, .refreshStage, .completeOnboarding,
             .createRecord, .createPlan, .updateDayTaskCompletion,
             .instantHelp, .createFeedback, .markFeedbackViewed,
             .submitDecision, .messageClicked, .messageDelivered,
             .registerDevice, .uploadFile,
             .bindChannel, .voiceConverse, .voiceTranscribe, .voiceSynthesize,
             .runSleepAnalysis:
            return "POST"
        case .unbindChannel:
            return "DELETE"
        case .initializeMemory:
            return "POST"
        }
    }

    public var path: String {
        switch self {
        case .health:
            return "/health"

        // Auth
        case .register:
            return "/api/v1/auth/register"
        case .login:
            return "/api/v1/auth/login"
        case .refreshToken:
            return "/api/v1/auth/refresh"

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
        case .listPlans:
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

        // Devices
        case .registerDevice:
            return "/api/v1/devices"

        // Plans (Focus Note)
        case .appendFocusNote(let planId, _):
            return "/api/v1/plans/\(planId.uuidString)/focus-note"

        // Files
        case .uploadFile:
            return "/api/v1/files/upload"

        // Consult Prep
        case .getConsultPrep:
            return "/api/v1/consult-prep"

        // Channels
        case .listChannelBindings:
            return "/api/v1/channels"
        case .bindChannel:
            return "/api/v1/channels/bind"
        case .unbindChannel(let id):
            return "/api/v1/channels/\(id.uuidString)"
        case .getChannelPreferences:
            return "/api/v1/channels/preferences"
        case .updateChannelPreferences:
            return "/api/v1/channels/preferences"
        case .wechatQRCode:
            return "/api/v1/channels/wechat/qrcode"

        // Voice
        case .voiceConverse:
            return "/api/v1/voice/converse"
        case .voiceTranscribe:
            return "/api/v1/voice/transcribe"
        case .voiceSynthesize:
            return "/api/v1/voice/synthesize"

        // Skills
        case .listSkills:
            return "/api/v1/skills"
        case .runSleepAnalysis:
            return "/api/v1/skills/sleep-analysis"
        case .initializeMemory:
            return "/api/v1/memory/initialize"
        }
    }

    // MARK: - Cached Formatter

    /// 缓存 ISO8601DateFormatter 避免每次查询创建新实例
    private static let iso8601Formatter: ISO8601DateFormatter = {
        let f = ISO8601DateFormatter()
        f.formatOptions = [.withInternetDateTime]
        return f
    }()

    public var queryItems: [URLQueryItem]? {
        switch self {
        case .listRecords(let childId, let limit, let before, let type):
            var items = [
                URLQueryItem(name: "child_id", value: childId.uuidString),
                URLQueryItem(name: "limit", value: String(limit))
            ]
            if let before {
                items.append(URLQueryItem(name: "before", value: Self.iso8601Formatter.string(from: before)))
            }
            if let type {
                items.append(URLQueryItem(name: "type", value: type))
            }
            return items

        case .getActivePlan(let childId):
            return [URLQueryItem(name: "child_id", value: childId.uuidString)]

        case .listPlans(let childId, let limit, let offset):
            return [
                URLQueryItem(name: "child_id", value: childId.uuidString),
                URLQueryItem(name: "limit", value: String(limit)),
                URLQueryItem(name: "offset", value: String(offset))
            ]

        case .homeSummary(let childId):
            return [URLQueryItem(name: "child_id", value: childId.uuidString)]

        case .listMessages(let limit, let before):
            var items = [URLQueryItem(name: "limit", value: String(limit))]
            if let before {
                items.append(URLQueryItem(name: "before", value: Self.iso8601Formatter.string(from: before)))
            }
            return items

        case .getConsultPrep(let childId):
            return [URLQueryItem(name: "child_id", value: childId.uuidString)]

        default:
            return nil
        }
    }

    public var body: (any Encodable & Sendable)? {
        switch self {
        case .register(let data): return data
        case .login(let data): return data
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
        case .registerDevice(let data): return data
        case .appendFocusNote(_, let data): return data
        case .bindChannel(let data): return data
        case .updateChannelPreferences(let data): return data
        case .voiceConverse(let data): return data
        case .voiceTranscribe(let data): return data
        case .voiceSynthesize(let data): return data
        case .runSleepAnalysis(let data): return data
        case .initializeMemory(let data): return data
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
        case .register, .createChild, .createRecord, .createPlan, .instantHelp, .registerDevice, .uploadFile, .bindChannel, .initializeMemory:
            return 201
        case .createFeedback:
            return 202
        case .unbindChannel:
            return 204
        default:
            return 200
        }
    }
}
