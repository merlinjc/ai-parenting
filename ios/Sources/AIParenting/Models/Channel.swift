import Foundation

// MARK: - Channel Binding

/// 渠道绑定响应
public struct ChannelBindingResponse: Codable, Sendable, Identifiable {
    public let id: UUID
    public let userId: UUID
    public let channel: String
    public let channelUserId: String
    public let deviceId: UUID?
    public let displayLabel: String?
    public let isActive: Bool
    public let verifiedAt: Date?
    public let createdAt: Date
    public let updatedAt: Date
}

/// 绑定渠道请求
public struct ChannelBindingCreate: Codable, Sendable {
    public let channel: String
    public let channelUserId: String
    public let deviceId: UUID?
    public let displayLabel: String?

    public init(channel: String, channelUserId: String, deviceId: UUID? = nil, displayLabel: String? = nil) {
        self.channel = channel
        self.channelUserId = channelUserId
        self.deviceId = deviceId
        self.displayLabel = displayLabel
    }
}

/// 渠道绑定列表响应
public struct ChannelBindingListResponse: Codable, Sendable {
    public let bindings: [ChannelBindingResponse]
}

// MARK: - Channel Preference

/// 渠道偏好更新请求
public struct ChannelPreferenceUpdate: Codable, Sendable {
    public var channelPriority: [String]?
    public var quietStartHour: Int?
    public var quietEndHour: Int?
    public var maxDailyPushes: Int?

    public init(channelPriority: [String]? = nil, quietStartHour: Int? = nil, quietEndHour: Int? = nil, maxDailyPushes: Int? = nil) {
        self.channelPriority = channelPriority
        self.quietStartHour = quietStartHour
        self.quietEndHour = quietEndHour
        self.maxDailyPushes = maxDailyPushes
    }
}

/// 渠道偏好响应
public struct ChannelPreferenceResponse: Codable, Sendable {
    public let id: UUID
    public let userId: UUID
    public let channelPriority: [String]
    public let quietStartHour: Int
    public let quietEndHour: Int
    public let maxDailyPushes: Int
    public let createdAt: Date
    public let updatedAt: Date
}

// MARK: - WeChat OAuth

/// 微信二维码响应
public struct WeChatQRCodeResponse: Codable, Sendable {
    public let qrcodeUrl: String
    public let state: String
    public let expiresIn: Int
}

// MARK: - Channel Display Helpers

/// 渠道类型展示助手
public enum ChannelType: String, CaseIterable {
    case apns
    case wechat
    case whatsapp
    case telegram
    case openclawWhatsapp = "openclaw_whatsapp"
    case openclawTelegram = "openclaw_telegram"

    public var displayName: String {
        switch self {
        case .apns: return "iOS 推送"
        case .wechat: return "微信"
        case .whatsapp, .openclawWhatsapp: return "WhatsApp"
        case .telegram, .openclawTelegram: return "Telegram"
        }
    }

    public var iconName: String {
        switch self {
        case .apns: return "iphone"
        case .wechat: return "message.fill"
        case .whatsapp, .openclawWhatsapp: return "phone.fill"
        case .telegram, .openclawTelegram: return "paperplane.fill"
        }
    }

    public var brandColor: String {
        switch self {
        case .apns: return "blue"
        case .wechat: return "green"
        case .whatsapp, .openclawWhatsapp: return "green"
        case .telegram, .openclawTelegram: return "blue"
        }
    }

    /// 是否通过 OpenClaw Gateway 中转
    public var isGatewayChannel: Bool {
        switch self {
        case .openclawWhatsapp, .openclawTelegram: return true
        default: return false
        }
    }
}
